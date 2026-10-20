"""score.py — rank clip candidates by how strong their first seconds are.

Only re-orders candidates that already passed every quality check in clips.py,
so it can change *which* good clips are chosen, never make a clip worse.

Signals, all measured on the hook window (first HOOK_S seconds) of each clip:
  voice   energy swing, pitch variation (monotone vs animated), speaking speed,
          dead air before / inside the hook                     — local, free
  picture face size, motion, camera cuts                        — local, free
  look    the AI views HOOK_FRAMES frames: expression and visual
          interest, 1-10 (NYO glm-5.3-flash, ~$0.0001 a frame)
  rank    the AI's own ranking of the moment from the transcript

Signals are compared *within the video* (robust z-scores), then weighted by
content category: a gaming clip is judged on motion and energy, a podcast on
voice and face. Weights are starting values; tune them from real view counts.
"""

import base64, concurrent.futures as cf, json, re, subprocess

import numpy as np

import clips as C

HOOK_S      = 3.0         # the window that decides whether people keep watching
HOOK_FRAMES = 3           # frames the AI looks at per candidate
LOOK_MODEL  = "glm-5.3-flash"   # sees images (tested); minicpm-v-4.5 also works

CATEGORIES = ["podcast", "talk", "education", "motivation", "comedy", "drama",
              "news", "gaming", "sports", "music", "other"]

# how much each signal counts, per category (signals are z-scores within the video)
_TALK = dict(rank=1.2, look=1.0, pitch=1.0, energy=0.8, rate=0.6, dead=-1.0,
             face=0.8, motion=0.2, cuts=0.1)
WEIGHTS = {
    "podcast": _TALK, "talk": _TALK, "education": dict(_TALK, rate=0.3, rank=1.4),
    "motivation": dict(_TALK, pitch=1.2, energy=1.0),
    "comedy": dict(_TALK, look=1.3, pitch=1.0, energy=1.0, motion=0.5),
    "drama": dict(_TALK, look=1.3, face=1.0, motion=0.5),
    "news": dict(_TALK, rank=1.5, rate=0.4, pitch=0.6),
    "gaming": dict(rank=0.8, look=1.0, pitch=0.2, energy=1.2, rate=0.1, dead=-0.3,
                   face=0.2, motion=1.2, cuts=1.0),
    "sports": dict(rank=0.6, look=1.0, pitch=0.2, energy=1.2, rate=0.1, dead=-0.2,
                   face=0.2, motion=1.3, cuts=1.0),
    "music": dict(rank=0.4, look=1.0, pitch=0.3, energy=1.3, rate=0.0, dead=-0.2,
                  face=0.5, motion=1.0, cuts=1.0),
    "other": _TALK,
}

LABEL = dict(rank="strong line", look="striking picture", pitch="animated voice",
             energy="punchy delivery", rate="fast pace", dead="no dead air",
             face="close face", motion="movement", cuts="quick cuts")


# ---------------- category ----------------

def category(sentences, forced=None):
    """Content category from the opening of the transcript (one cheap request)."""
    if forced:
        return forced if forced in WEIGHTS else "other"
    text = "\n".join(t for _, t, _ in sentences[:60])[:4000]
    if not text.strip():
        return "other"
    ans = C.chat("Which ONE category fits this video best? Answer with only the word.\n"
                 f"Categories: {', '.join(CATEGORIES)}\n\nTranscript start:\n{text}",
                 max_tokens=1500) or ""
    found = re.findall("|".join(CATEGORIES), ans.lower())
    return found[-1] if found else "other"


# ---------------- signals ----------------

def _pitch(seg, sr=16000):
    """Pitch per 40 ms frame (autocorrelation, 70-400 Hz); NaN where unvoiced."""
    n, hop = int(0.04 * sr), int(0.01 * sr)
    lo, hi = sr // 400, sr // 70
    out = []
    for i in range(0, len(seg) - n, hop):
        f = seg[i:i + n] - seg[i:i + n].mean()
        if np.sqrt(np.mean(f ** 2)) < 0.01:
            out.append(np.nan); continue
        ac = np.correlate(f, f, "full")[n - 1:]
        k = lo + int(np.argmax(ac[lo:hi]))
        out.append(sr / k if ac[k] > 0.3 * ac[0] else np.nan)
    return np.array(out)


def voice(audio, words, s, e):
    """energy swing, pitch variation (semitones), words/second, dead air (s)."""
    a = audio[int(s * 16000):int(e * 16000)]
    if len(a) < 1600:
        return dict(energy=0, pitch=0, rate=0, dead=e - s)
    n = len(a) // 160
    db = 20 * np.log10(np.sqrt(np.mean(a[:n * 160].reshape(n, 160) ** 2, axis=1)) + 1e-9)
    loud = db[db > np.percentile(db, 30)]
    f0 = _pitch(a)
    f0 = f0[~np.isnan(f0)]
    semis = 12 * np.log2(f0 / np.median(f0)) if len(f0) > 5 else np.zeros(1)
    inside = [w for w in words if s <= w["s"] < e]
    gaps = [b["s"] - a_["e"] for a_, b in zip(inside, inside[1:])]
    lead = (inside[0]["s"] - s) if inside else e - s
    return dict(energy=float(np.std(loud)) if len(loud) else 0.0,
                pitch=float(np.std(semis)),
                rate=len(inside) / (e - s),
                dead=float(lead + sum(g for g in gaps if g > 0.3)))


def picture(video, s, e, det_size):
    """largest face share of the frame, motion, cuts — over the hook window."""
    import cv2
    cap = cv2.VideoCapture(str(video))
    w, h = det_size
    det = cv2.FaceDetectorYN.create(str(C.MODELS_DIR / "yunet.onnx"), "", (w, h), 0.6, 0.3, 5000)
    faces, diffs, prev, t = [], [], None, s
    while t < e:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, fr = cap.read()
        if not ok:
            break
        if len(faces) < 4 and abs((t - s) % 0.75) < 0.1:
            _, f = det.detect(fr)
            f = [x for x in (f if f is not None else []) if x[14] >= C.FACE_CONF]
            faces.append(max((x[2] * x[3] for x in f), default=0) / (w * h))
        g = cv2.cvtColor(cv2.resize(fr, (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.float32)
        if prev is not None:
            diffs.append(float(np.mean(np.abs(g - prev))))
        prev, t = g, t + 0.2
    cap.release()
    return dict(face=float(np.mean(faces)) if faces else 0.0,
                motion=float(np.median(diffs)) if diffs else 0.0,
                cuts=float(len(C.shot_cuts(video, s, e))))


def look(video, s, e, cat):
    """The AI views a few frames of the hook: expression and visual interest 1-10."""
    imgs = []
    w, h, cw, ch, y = C.crop_geometry(video)
    shots = C.plan_shots(video, s, e)
    for k in range(HOOK_FRAMES):
        rel = (e - s) * (k + 0.5) / HOOK_FRAMES
        t = s + rel
        # judge the frame as the viewer will see it: the face crop, not the wide shot
        shot = next((x for x in shots if x[0] <= rel < x[1]), shots[-1])
        vf = "scale=384:-2"
        if shot[2] == "crop" and shot[3]:
            fx = min(shot[3], key=lambda q: abs(q[0] - rel))[1]
            x = int(max(0, min(fx - cw / 2, w - cw)))
            vf = f"crop={cw}:{ch}:{x}:{y},scale=270:-2"
        r = subprocess.run([C.FFMPEG, "-v", "error", "-ss", f"{t:.2f}", "-i", str(video),
                            "-frames:v", "1", "-vf", vf, "-q:v", "5",
                            "-f", "image2pipe", "-vcodec", "mjpeg", "-"], capture_output=True)
        if r.stdout:
            imgs.append(base64.b64encode(r.stdout).decode())
    if not imgs:
        return 5.0, ""
    content = [{"type": "text", "text":
                f"These are frames from the first {HOOK_S:.0f} seconds of a vertical {cat} "
                "short video, exactly as viewers see them on a phone. "
                "Would they stop someone scrolling? Judge facial expression, emotion, "
                "action and visual interest. Reply ONLY with JSON: "
                '{"score": 1-10, "why": "max 8 words"}'}]
    content += [{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{i}"}}
                for i in imgs]
    txt = C.chat(content, model=LOOK_MODEL, max_tokens=1500) or ""
    m = re.search(r"\{.*\}", txt, re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
        return float(d.get("score", 5)), str(d.get("why", ""))[:60]
    except (ValueError, TypeError):
        return 5.0, ""


# ---------------- ranking ----------------

def _z(xs):
    xs = np.asarray(xs, float)
    mad = np.median(np.abs(xs - np.median(xs))) * 1.4826
    sd = mad if mad > 1e-9 else (xs.std() or 1.0)
    return np.clip((xs - np.median(xs)) / sd, -3, 3)


def rank(video, audio, words, picks, cat, use_ai=True):
    """Score every candidate, return them best first with score and reasons."""
    if not picks:
        return picks
    size = C.frame_size(video)
    def one(i_p):
        i, p = i_p
        s, e = p["start"], min(p["start"] + HOOK_S, p["end"])
        sig = voice(audio, words, s, e)
        sig.update(picture(video, s, e, size))
        sig["rank"] = -i                       # AI's order: earlier = stronger
        sig["look"], p["look_why"] = look(video, s, e, cat) if use_ai else (5.0, "")
        return sig
    with cf.ThreadPoolExecutor(4) as ex:
        sigs = list(ex.map(one, enumerate(picks)))
    w = WEIGHTS.get(cat, WEIGHTS["other"])
    z = {k: _z([s[k] for s in sigs]) for k in w}
    for j, p in enumerate(picks):
        parts = {k: w[k] * z[k][j] for k in w}
        p["score"] = round(50 + 10 * sum(parts.values()) / sum(abs(v) for v in w.values()) * 3, 1)
        p["signals"] = {k: round(sigs[j][k], 3) for k in w}
        best = sorted(parts, key=parts.get, reverse=True)[:2]
        p["why_score"] = ", ".join(LABEL[k] for k in best if parts[k] > 0) or "average on every signal"
    return sorted(picks, key=lambda p: -p["score"])
