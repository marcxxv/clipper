#!/usr/bin/env python3
"""clips.py — any video in, postable vertical captioned shorts out.

  audio → local transcript (word timings snapped to the audio)
        → mode by video type: clips (talk) · reedit (trailer) · visual (no speech)
        → AI picks moments (NYO glm-5.3-flash) → snapped to clean sentences
        → per-shot framing (face crop / two-speaker split / padded) → karaoke captions
        → clips + post text + report + contact sheet, each file checked

Usage:  python clips.py "<video or YouTube link>" [--mode=clips|reedit|visual] [--headline]
        python clips.py --check        test the setup
Docs:   README.md and docs/ at the repo root.
"""

import json, os, re, shutil, subprocess, sys, time
from itertools import zip_longest
from pathlib import Path

import requests

if hasattr(sys.stdout, "reconfigure"):          # Windows consoles default to cp1252
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---------------- config ----------------
ROOT        = Path(__file__).parent             # <repo>/pipeline
REPO        = ROOT.parent
IN, OUTROOT = REPO / "sources", REPO / "output"
MODELS_DIR  = ROOT / "models"
SKILL       = REPO / ".agents/skills/clipping/SKILL.md"  # editorial rules, one copy
PROFILE     = Path.home() / ".hermes/profiles/clipper"   # optional Hermes agent

MODEL       = "glm-5.3-flash"
FALLBACK    = ["glm-5.3-flash", "glm-5", "qwen3-30b"]
WHISPER     = "large-v3-turbo"

N_CLIPS     = 10          # final clips
CANDIDATES  = 15          # asked from the model, best N survive
MIN_S, MAX_S = 22, 45     # clip length window
GAP         = 1.5         # min seconds between clips
ROUNDS      = 2           # ask the model again if too few picks survive
SNAP        = 6           # how far a start may move to reach a clean sentence
HIGHLIGHT   = "&H001FD9FF&" # amber, ASS BGR
FONTS       = ROOT / "fonts"          # Montserrat (SIL OFL), loaded by the ass filter
CAP_FONT    = "Montserrat Black"
CAP_SIZE    = 84
CAP_POP     = 120         # % the spoken word swells to
EASE_IN     = 60          # ms for the spoken word to turn amber and swell
EASE_OUT    = 80          # ms for the previous word to settle back to white
GROUP_GAP   = 0.35        # a pause this long ends the caption line (nothing shown in silence)
HEADLINE    = False       # top hook text on normal clips (also: --headline); re-edits always have one
HOLD        = 0.10        # last word of a line lingers this long, unless the next line starts
DIP_WIN     = 12          # x10 ms: how far a word boundary may move to a loudness dip
TIMING      = "energy-v4" # word timings snapped to the audio; bump to re-refine caches
OUT_W, OUT_H = 1080, 1920
SAFE_BOTTOM = 420         # TikTok/Reels buttons and caption cover the bottom ~20%
SCENE_CUT   = 0.3         # ffmpeg scene score that counts as a camera cut
MIN_SHOT    = 0.4         # shorter flashes are merged into the previous shot
FACE_SHARE  = 0.6         # share of samples with a face to crop instead of pad
CHUNK_MIN   = 40          # long sources are read by the model in windows this long
QUIET_WPM   = 40          # under this many words a minute it is not a talking video
FASTCUT_CPM = 12          # camera cuts a minute that mark a trailer / promo edit
LANG        = "en"        # set from the transcript
NOSPACE     = {"ja", "zh", "yue", "th", "lo", "km", "my"}   # written without spaces
PAUSE       = 0.7         # silence that ends a sentence when the transcript has no punctuation
FACE_CONF   = 0.85        # detector confidence; statues and posters score ~0.6-0.8

API = "https://llm.nyolab.ai/api/public/v1/chat/completions"
USED = {"model": None}
# ----------------------------------------


def _find_ffmpeg():
    """Prefer a build that has libass (needed to burn captions)."""
    cands = [os.environ.get("CLIPS_FFMPEG", ""),
             str(Path.home() / ".hermes/tools/ffmpeg-9.0.1-darwin-arm64/ffmpeg"),
             "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",     # Homebrew's build with libass
             "/usr/local/opt/ffmpeg-full/bin/ffmpeg",
             "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg", shutil.which("ffmpeg") or ""]
    for c in cands:
        if not c:
            continue
        try:
            out = subprocess.run([c, "-hide_banner", "-filters"],
                                 capture_output=True, text=True).stdout
            if re.search(r" (ass|subtitles) ", out):
                return c
        except (FileNotFoundError, OSError):
            continue
    sys.exit("no ffmpeg with libass found")


FFMPEG  = _find_ffmpeg()
FFPROBE = next((c for c in [str(Path(FFMPEG).with_name("ffprobe" + Path(FFMPEG).suffix)),
                            shutil.which("ffprobe") or "",
                            "/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe"]
                 if c and Path(c).exists()), "ffprobe")

OUT = OUTROOT   # rebound per video in main()


KEY_NAMES = ("NYO_API_KEY", "HERMES_CUSTOM_NYOLAB_API_KEY")


def api_key():
    """NYO key: environment, then the repo's .env, then a Hermes clipper profile."""
    for k in KEY_NAMES:
        if os.environ.get(k):
            return os.environ[k]
    for env in (REPO / ".env", PROFILE / ".env", Path.home() / ".hermes/.env"):
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if k.strip() in KEY_NAMES and v.strip():
                return v.strip().strip('"').strip("'")
    sys.exit("no NYO key: put NYO_API_KEY=... in the .env file at the repo root (see .env.example)")


def sh(cmd):
    # cwd=ROOT so caption files can be passed as relative paths: a Windows
    # drive letter ("C:") breaks ffmpeg's filter syntax
    r = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", cwd=ROOT)
    if r.returncode:
        sys.exit(f"failed: {' '.join(str(c) for c in cmd[:6])}...\n{r.stderr[-800:]}")
    return r.stdout


def duration(path):
    return float(sh([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                     "-of", "csv=p=0", str(path)]).strip())


def frame_size(video):
    wh = sh([FFPROBE, "-v", "error", "-select_streams", "v",
             "-show_entries", "stream=width,height", "-of", "csv=p=0",
             str(video)]).strip().split(",")[:2]
    return int(wh[0]), int(wh[1])


# ---------------- transcription ----------------

def transcribe(video):
    import numpy as np
    from faster_whisper import WhisperModel

    cache = OUT / f"{video.stem}.transcript.json"
    if cache.exists():
        d = json.loads(cache.read_text(encoding="utf-8"))
        set_lang(d.get("lang", "en"))
        print(f"   cached transcript ({len(d['words'])} words, {LANG})")
        if d.get("timing") != TIMING:                 # rules changed: refine again from raw
            d.setdefault("raw", d["words"])
            d["words"] = refine_timing(d["raw"], _audio(video))
            d["timing"] = TIMING
            cache.write_text(json.dumps(d), encoding="utf-8")
        lines = [tuple(x) for x in d["lines"]]
        return mark_breaks(d["words"], lines), lines

    print("   decoding audio...")
    audio = _audio(video)

    print(f"   transcribing {len(audio)/16000/60:.1f} min...")
    model = WhisperModel(WHISPER, device="cpu", compute_type="int8")
    segs, info = model.transcribe(audio, word_timestamps=True, vad_filter=True)
    set_lang(info.language)
    words, lines = [], []
    for s in segs:
        for w in (s.words or []):
            words.append({"w": w.word.strip(), "s": float(w.start), "e": float(w.end)})
        if s.text.strip():
            lines.append((float(s.start), s.text.strip()))
    raw, words = words, refine_timing(words, audio)
    cache.write_text(json.dumps({"words": words, "raw": raw, "lines": lines,
                                 "lang": LANG, "timing": TIMING}), encoding="utf-8")
    print(f"   language: {LANG}")
    return mark_breaks(words, lines), lines


def _audio(video):
    import numpy as np
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(video),
                          "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True)
    if raw.returncode:
        sys.exit(f"audio decode failed: {raw.stderr.decode()[-500:]}")
    return np.frombuffer(raw.stdout, np.float32)


def refine_timing(words, audio, dips=True):
    """Whisper glues pauses onto the next word (measured: 60% of real pauses hidden).
    Trim each word to where its sound actually starts and stops, so the caption
    highlight lands on the word as it is spoken and nothing shows during silence."""
    import numpy as np
    n = len(audio) // 160                                   # 10 ms frames
    if not n or not words:
        return words
    db = 20 * np.log10(np.sqrt(np.mean(audio[:n * 160].reshape(n, 160) ** 2, axis=1)) + 1e-9)
    loud = db[db > np.percentile(db, 40)]
    thr = (np.median(loud) if len(loud) else db.max()) - 18  # speech level minus 18 dB
    voiced = db >= thr
    moved, out = 0, []
    for w in words:
        i0, i1 = int(w["s"] * 100), min(int(w["e"] * 100) + 1, n)
        w = dict(w)
        run = _voice_run(voiced[i0:i1])
        if run:                                             # at least 40 ms of voice
            s, e = (i0 + run[0]) / 100 - 0.02, (i0 + run[1]) / 100 + 0.03
            if s - w["s"] > 0.05 or w["e"] - e > 0.05:
                moved += 1
            w["s"], w["e"] = max(w["s"], s), min(w["e"], e)
        if out and w["s"] < out[-1]["s"] + 0.02:            # keep order
            w["s"] = out[-1]["s"] + 0.02
        w["e"] = max(w["e"], w["s"] + 0.06)
        out.append(w)
    # words that run together: put the boundary in the loudness dip between them
    for a, b in zip(out, out[1:]) if dips else ():
        if b["s"] - a["e"] < 0.10:
            mid = int((a["e"] + b["s"]) * 50)
            lo = max(mid - DIP_WIN, int(a["s"] * 100) + 6)
            hi = min(mid + DIP_WIN + 1, int(b["e"] * 100) - 6)
            if hi > lo:
                cut = (lo + int(np.argmin(db[lo:hi]))) / 100
                if abs(cut - b["s"]) > 0.03:
                    moved += 1
                a["e"], b["s"] = min(a["e"], cut), max(cut, a["s"] + 0.06)
    print(f"   timing: {moved} of {len(words)} word edges snapped to the audio")
    return out


def _voice_run(v):
    """The burst of voice inside a word's window. Whisper often stretches a word
    across a pause; the word itself is the longest burst (later one on a tie,
    since the stretch is usually backwards over the silence)."""
    import numpy as np
    idx = np.flatnonzero(v)
    if len(idx) < 4:
        return None
    runs, a = [], idx[0]
    for x, y in zip(idx, idx[1:]):
        if y - x > 15:                                      # >150 ms of silence splits
            runs.append((a, x + 1))
            a = y
    runs.append((a, idx[-1] + 1))
    return max(reversed(runs), key=lambda r: r[1] - r[0] + 3 * (r is runs[-1]))


def set_lang(code):
    global LANG
    LANG = code or "en"


# ---------------- hook selection ----------------

def editorial_rules():
    """The part of the clipping skill the AI needs: between the brief markers."""
    if not SKILL.exists():
        return ""
    m = re.search(r"<!-- brief:start -->(.*?)<!-- brief:end -->",
                  SKILL.read_text(encoding="utf-8"), re.S)
    return m.group(1).strip() if m else ""


def _prompt(transcript, total, taken=()):
    mins = int(total // 60)
    avoid = ("- These ranges are already used, pick nothing that overlaps them: "
             + ", ".join(f"{a:.0f}-{b:.0f}s" for a, b in taken) + "\n") if taken else ""
    brief = editorial_rules()
    return (
        f"You are a short-form video editor cutting a {mins}-minute video into vertical clips.\n\n"
        f"Pick the {CANDIDATES} strongest standalone moments, ordered strongest first.\n\n"
        + (brief + "\n\n" if brief else "")
        + f"- Each clip must be {MIN_S}-{MAX_S} seconds.\n"
        "- Never overlap two clips.\n" + avoid
        + f"- Write hook, title and hashtags in the transcript's own language ({LANG}).\n\n"
        "Return ONLY JSON, no prose, no code fences:\n"
        '[{"start": 12.5, "end": 48.0, "hook": "exact opening words",\n'
        '  "title": "punchy title under 60 characters",\n'
        '  "headline": "on-screen hook text, max 6 words",\n'
        '  "hashtags": ["#one", "#two", "#three"],\n'
        '  "reason": "why it works, max 8 words"}]\n\n'
        "Transcript:\n" + transcript
    )


def _ask(prompt, want):
    """Try each model until one actually returns parseable JSON."""
    for model in FALLBACK:
        r = requests.post(API, timeout=300,
                          headers={"Authorization": f"Bearer {api_key()}"},
                          json={"model": model, "temperature": 0.4, "max_tokens": 16000,
                                "messages": [{"role": "user", "content": prompt}]})
        tag = f"{model:14s}"
        if r.status_code != 200:
            try:
                msg = r.json()["error"]["message"][:110]
            except Exception:
                msg = r.text[:110]
            print(f"   ! {tag} {r.status_code} — {msg}")
            continue
        txt = (r.json()["choices"][0]["message"]["content"] or "").strip()
        txt = re.sub(r"^```(?:json)?|```$", "", txt, flags=re.M).strip()
        i = txt.find("[")
        if i < 0:
            print(f"   ! {tag} empty reply")
            continue
        try:                                   # read the first JSON list, ignore trailing chatter
            raw = json.JSONDecoder().raw_decode(txt[i:])[0][:want]
        except json.JSONDecodeError as e:
            print(f"   ! {tag} bad JSON: {e}")
            continue
        print(f"   ok {tag} {len(raw)} candidates")
        USED["model"] = model
        return raw
    return []


FILLERS = {"and", "but", "so", "like", "okay", "well", "now", "yes", "no", "yeah", "yep", "um", "uh",
           "oh", "right", "that", "it", "you", "i", "then", "because", "alright"}


def _first(w):
    return w["w"].lower().strip(",.?!\"'")


# characters that end or join phrases — a clip never opens on one
BAD_OPEN = {"ja": set("なねかよとがをにはでもだっゃゅょぁぃぅぇぉー、。"),
            "zh": set("的了吗呢吧啊么着过和与及而但、。，")}


def _bad_start(w):
    """Filler or mid-phrase opening: 'And…', 'So…', or a Japanese/Chinese particle."""
    return _first(w) in FILLERS or w["w"][:1] in BAD_OPEN.get(LANG, ())


def _punct(w):
    return w["w"].rstrip("\"')」』").endswith((".", "?", "!", "。", "？", "！"))


def _ends(w):
    return w.get("eos", _punct(w))


def mark_breaks(words, lines=()):
    """Flag sentence ends once. Japanese/Chinese transcripts often carry no
    punctuation at all; there the boundaries are pauses plus the transcriber's
    own phrase breaks (segment starts)."""
    use_pause = sum(map(_punct, words)) < len(words) * 0.01
    starts = sorted(t for t, _ in lines) if use_pause else []
    seg_end, j = set(), 0
    for t in starts:                              # word nearest each segment start
        while j + 1 < len(words) and abs(words[j + 1]["s"] - t) <= abs(words[j]["s"] - t):
            j += 1
        if j and abs(words[j]["s"] - t) < 0.5:
            seg_end.add(j - 1)
    # CJK pieces are sub-word (自 + 分), so a short pause inside a word is common
    pause = PAUSE * (1.7 if LANG in NOSPACE else 1)
    for i, w in enumerate(words):
        nxt = words[i + 1]["s"] if i + 1 < len(words) else None
        w["eos"] = (_punct(w) or nxt is None or i in seg_end
                    or (use_pause and nxt - w["e"] >= pause))
    return words


def joined(ws):
    """Words back into text: no spaces for languages written without them, and
    Whisper's split pieces ("26", "-year", "-old") glued back together."""
    out = ""
    for w in ws:
        t = w["w"] if isinstance(w, dict) else w
        bare = re.sub(r"\{[^}]*\}", "", t)          # ignore caption styling tags
        glue = LANG in NOSPACE or not out or bare[:1] in "-'’%" or out.endswith("-")
        out += t if glue else " " + t
    return out


def line_full(line):
    """Caption line is full: 3 words, or ~9 characters of CJK / 20 of Latin."""
    return len(line) >= 3 or len(joined(line)) > (9 if LANG in NOSPACE else 20)


def _capital(w):
    """Sentence-case check that lets scripts without capitals (日本語, العربية) through."""
    c = w["w"][:1]
    return c.isupper() or c.lower() == c.upper()


# words that never deserve the highlight, however long they are
PLAIN = FILLERS | {
    "about", "after", "again", "always", "another", "anything", "around", "because",
    "before", "being", "between", "could", "doesn't", "don't", "every", "everyone",
    "everything", "going", "gonna", "have", "having", "he's", "here", "i'm", "it's",
    "just", "maybe", "might", "people", "really", "should", "somebody", "someone",
    "something", "that's", "their", "there", "there's", "these", "they", "they're",
    "they've", "thing", "things", "think", "those", "through", "we're", "what's",
    "where", "which", "while", "would", "you'll", "you're", "you've", "yourself",
}


def snap_start(words, s):
    """Move a start onto the nearest real sentence opening that isn't a filler."""
    starts = [w for i, w in enumerate(words)
              if (i == 0 or _ends(words[i - 1])) and -SNAP <= w["s"] - s <= SNAP]
    good = [w for w in starts if not _bad_start(w) and _capital(w)]
    pool = good or starts
    return min(pool, key=lambda w: abs(w["s"] - s))["s"] - 0.05 if pool else s


def snap_end(words, s, e):
    """End just after a sentence closes, never mid-sentence."""
    ends = [w for w in words if _ends(w) and s + MIN_S - 1 <= w["e"] <= min(e + 3, s + MAX_S)]
    return min(ends, key=lambda w: abs(w["e"] - e))["e"] + 0.25 if ends else e


def align(words, s, e):
    """If a cut lands inside a word, move it outside that word."""
    for w in words:
        if w["s"] < s < w["e"]:
            s = w["e"] + 0.05
        if w["s"] < e < w["e"]:
            e = w["e"] + 0.05
    return s, e


def opening(words, s, n=16):
    """The words a viewer actually hears first, up to the first sentence end."""
    out = []
    for w in (w for w in words if w["s"] >= s):
        out.append(w["w"])
        if _ends(w) or len(out) >= n:
            break
    return joined(out)


def sentences(words):
    """(start, text, end) per sentence, so the model's timestamps land on sentence starts."""
    out, cur = [], []
    for w in words:
        cur.append(w)
        if _ends(w):
            out.append((cur[0]["s"], joined(cur), cur[-1]["e"]))
            cur = []
    if cur:
        out.append((cur[0]["s"], joined(cur), cur[-1]["e"]))
    return out


def _windows(words, total):
    """Transcript text per window, so a 3-hour podcast never overflows the model."""
    sents = sentences(words)
    n = max(1, int(-(-total // (CHUNK_MIN * 60))))
    span = total / n
    out = []
    for k in range(n):
        part = [(t, x) for t, x, _ in sents if k * span <= t < (k + 1) * span]
        out.append("\n".join(f"[{int(t//60):02d}:{t%60:04.1f}] {x}" for t, x in part))
    return out, span


def _ask_all(windows, span, taken):
    """One request per window, results interleaved so no window dominates."""
    if len(windows) == 1:
        return _ask(_prompt(windows[0], span, taken), CANDIDATES)
    want = max(4, CANDIDATES // len(windows) + 2)
    lists = [_ask(_prompt(w, span, taken), want) for w in windows]
    return [c for row in zip_longest(*lists) for c in row if c]


def pick_hooks(lines, words, total):
    windows, span = _windows(words, total)
    if len(windows) > 1:
        print(f"   long source: reading in {len(windows)} windows of {span/60:.0f} min")
    picks = []
    for rnd in range(ROUNDS):                          # top up if the checks reject too many
        if len(picks) >= N_CLIPS:
            break
        taken = [(p["start"], p["end"]) for p in picks]
        cands = _ask_all(windows, span, taken)
        if not cands and not picks:
            sys.exit("model returned nothing usable")
        before = len(picks)
        _validate(cands, words, total, picks)
        print(f"   round {rnd + 1}: {len(picks) - before} of {len(cands)} passed the checks")

    picks = picks[:N_CLIPS]                            # model order = strongest first
    picks.sort(key=lambda p: p["start"])
    return picks


def _validate(cands, words, total, picks):
    """Snap each candidate to clean sentences; keep it only if it passes every rule."""
    for c in cands:
        try:
            s = float(c["start"])
            e = min(float(c["end"]), s + MAX_S)
        except (KeyError, TypeError, ValueError):
            continue

        if s > 2.5:                                   # 0:00 is usually a cold open
            s = snap_start(words, s)
        e = snap_end(words, s, e)
        s, e = align(words, s, e)
        s = max(0.0, min(s, total - MIN_S))
        e = max(s + 5, min(e, total))

        if not (MIN_S - 1 <= e - s <= MAX_S):
            continue
        first = [w for w in words if w["s"] >= s][:1]
        if first and (_bad_start(first[0]) or not _capital(first[0])):
            continue
        if any(s < p["end"] + GAP and e > p["start"] - GAP for p in picks):
            continue                                   # overlaps a stronger pick

        picks.append({
            "start": s, "end": e,
            "hook": opening(words, s), "title": c.get("title", ""),
            "hashtags": c.get("hashtags", [])[:4], "reason": c.get("reason", ""),
            "headline": (c.get("headline") or "")[:48],
        })


# ---------------- captions ----------------

def ass_time(t):
    t = max(0.0, t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def caption_groups(words):
    """Lines of up to 3 words. A line ends at a sentence end or at any pause, so
    the screen is empty while the speaker is silent."""
    groups, line = [], []
    for w in words:
        if line and (line_full(line) or _ends(line[-1]) or w["s"] - line[-1]["e"] > GROUP_GAP):
            groups.append(line)
            line = []
        line.append(w)
    if line:
        groups.append(line)
    return groups


def _esc(t):
    return t.replace("{", "(").replace("}", ")").replace("\\", "/")


def captions(words, start, end, path, marginv=250, headline=""):
    """Karaoke captions: the line appears as speech starts, the spoken word turns
    amber and swells the moment it is said, the line clears in pauses."""
    inside = [dict(w, s=w["s"] - start, e=min(w["e"], end) - start)
              for w in words if w["e"] > start and w["s"] < end]
    groups = caption_groups(inside)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {OUT_W}
PlayResY: {OUT_H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{CAP_FONT},{CAP_SIZE},&H00FFFFFF,&H00000000,&H78000000,0,1,9,4,2,70,70,{marginv},1
Style: Head,{CAP_FONT},60,&H00FFFFFF,&H00000000,&HB4000000,0,3,18,0,8,90,90,230,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    body = []
    if headline:
        body.append(f"Dialogue: 1,{ass_time(0)},{ass_time(end - start)},Head,,0,0,0,,"
                    + _esc(headline.upper()))
    for g, grp in enumerate(groups):
        nxt = groups[g + 1][0]["s"] if g + 1 < len(groups) else end - start
        for k, w in enumerate(grp):
            s = max(w["s"], 0)
            last = k + 1 == len(grp)
            e = grp[k + 1]["s"] if not last else min(w["e"] + HOLD, nxt - 0.02)
            e = max(e, s + 0.08)
            fin, fout = (70 if k == 0 else 0), (90 if last else 0)
            fade = rf"{{\fad({fin},{fout})}}" if fin or fout else ""
            parts = []
            for j, x in enumerate(grp):
                t = _esc(x["w"])
                if j == k:          # spoken now: eases into amber and swells
                    parts.append(rf"{{\fscx100\fscy100\t(0,{EASE_IN},\c{HIGHLIGHT}"
                                 rf"\fscx{CAP_POP}\fscy{CAP_POP})}}" + t + r"{\r}")
                elif j == k - 1:    # just spoken: eases back to white
                    parts.append(rf"{{\c{HIGHLIGHT}\fscx{CAP_POP}\fscy{CAP_POP}"
                                 rf"\t(0,{EASE_OUT},\c&H00FFFFFF&\fscx100\fscy100)}}" + t + r"{\r}")
                else:
                    parts.append(t)
            body.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,"
                        + fade + joined(parts))
    path.write_text(head + "\n".join(body) + "\n", encoding="utf-8")


def ass_filter(sub):
    rel = lambda p: os.path.relpath(p, ROOT).replace("\\", "/")
    return f"ass={rel(sub)}:fontsdir={rel(FONTS)}"


# ---------------- framing ----------------

def crop_geometry(video):
    w, h = frame_size(video)
    ar = OUT_W / OUT_H
    if w / h > ar:
        cw, ch = int(h * ar), h
    else:
        cw, ch = w, int(w / ar)
    cw, ch = cw // 2 * 2, ch // 2 * 2
    return w, h, cw, ch, int(max(0, (h - ch) / 2)) // 2 * 2


def shot_cuts(video, start, end):
    """Camera cuts inside the clip, in seconds from clip start."""
    r = subprocess.run([FFMPEG, "-hide_banner", "-ss", f"{start:.3f}", "-t", f"{end-start:.3f}",
                        "-i", str(video), "-an",
                        "-vf", f"scale=320:-2,select='gt(scene,{SCENE_CUT})',showinfo",
                        "-f", "null", "-"], capture_output=True, text=True)
    cuts = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", r.stderr)]
    # flashes shorter than MIN_SHOT get folded into the shot before them
    keep = []
    for c in cuts:
        if c - (keep[-1] if keep else 0) >= MIN_SHOT and (end - start) - c >= MIN_SHOT:
            keep.append(c)
    return keep


def faces_in(det, cap, t):
    import cv2
    cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
    ok, fr = cap.read()
    if not ok:
        return []
    _, faces = det.detect(fr)
    if faces is None or not len(faces):
        return []
    faces = sorted((f for f in faces if f[14] >= FACE_CONF), key=lambda q: -q[2] * q[3])
    return [(float(f[0] + f[2] / 2), float(f[1] + f[3] / 2), float(f[2] * f[3])) for f in faces]


def plan_shots(video, start, end):
    """Split the clip at camera cuts and choose a layout per shot.

      crop  — one face: tracking 9:16 crop, pts = [(t, face_x), ...]
      split — two people side by side: each stacked in half the frame,
              pts = [(left_x, left_y), (right_x, right_y)]
      pad   — wide shot, b-roll, title card, screen recording: never cropped
    Times are relative to clip start.
    """
    import cv2

    dur = end - start
    edges = [0.0] + shot_cuts(video, start, end) + [dur]
    model = MODELS_DIR / "yunet.onnx"
    cap = cv2.VideoCapture(str(video)) if model.exists() else None
    if cap is None or not cap.isOpened():
        return [(0.0, dur, "pad", [])]
    w, h = frame_size(video)
    det = cv2.FaceDetectorYN.create(str(model), "", (w, h), 0.6, 0.3, 5000)

    _, fh, cw, _, _ = crop_geometry(video)
    shots = []
    for t0, t1 in zip(edges, edges[1:]):
        n = max(3, min(int((t1 - t0) / 0.5), 40))      # ~2 samples a second
        ts = [t0 + (t1 - t0) * (i + 0.5) / n for i in range(n)]
        seen = [(t, faces_in(det, cap, start + t)) for t in ts]
        pts = [(t, f[0][0]) for t, f in seen if f]
        pairs = [sorted(f[:2]) for _, f in seen
                 if len(f) >= 2 and f[1][2] >= 0.4 * f[0][2]          # comparable size
                 and abs(f[0][0] - f[1][0]) > cw * 0.8                 # won't fit one crop
                 and abs(f[0][1] - f[1][1]) < fh * 0.2]                # heads level
        if len(pairs) >= n * FACE_SHARE:                # two people, too far apart for one crop
            med = lambda k, j: sorted(p[k][j] for p in pairs)[len(pairs) // 2]
            shots.append((t0, t1, "split", [(med(0, 0), med(0, 1)), (med(1, 0), med(1, 1))]))
            continue
        mode = "crop" if len(pts) >= n * FACE_SHARE else "pad"
        if mode == "crop" and len(pts) >= 3:              # smooth jitter
            xs = [x for _, x in pts]
            xs = [xs[0]] + [(xs[i-1] + xs[i] + xs[i+1]) / 3
                            for i in range(1, len(xs) - 1)] + [xs[-1]]
            pts = [(pts[i][0], xs[i]) for i in range(len(pts))]
        shots.append((t0, t1, mode, pts))
    cap.release()
    return shots


def pan_expr(pts, cw, w):
    """Crop x that glides between face samples inside one shot."""
    lo, hi = cw / 2, w - cw / 2
    pts = [(t, round((max(lo, min(x, hi)) - cw / 2) / 4) * 4) for t, x in pts]
    expr = f"{pts[-1][1]:.0f}"
    for i in range(len(pts) - 2, -1, -1):
        (ta, xa), (tb, xb) = pts[i], pts[i + 1]
        span = max(tb - ta, 0.01)
        expr = f"if(lt(t,{tb:.2f}),{xa:.0f}+({xb-xa:.0f})*(t-{ta:.2f})/{span:.2f},{expr})"
    return f"if(lt(t,{pts[0][0]:.2f}),{pts[0][1]:.0f},{expr})"


def track_expr(shots, cw, w):
    """Per-shot pan, jumping (not gliding) across camera cuts."""
    expr = None
    for t0, t1, mode, pts in reversed(shots):
        here = pan_expr(pts, cw, w) if mode == "crop" and pts else f"{(w - cw) // 2}"
        expr = here if expr is None else f"if(lt(t,{t1:.3f}),{here},{expr})"
    return expr


# ---------------- render ----------------

def slug(text, n=5):
    words = re.findall(r"[A-Za-z0-9']+", text.lower())[:n]
    return "-".join(words)[:44].strip("-") or "clip"


def caption_margin(video, mode=""):
    """Bottom margin that clears both platform UI and a padded 16:9 band.
    Two stacked speakers: on the seam between them, not over a face."""
    if "split" in mode and "pad" not in mode:     # a padded band would sit on the seam
        return OUT_H // 2 - 45
    w, h = frame_size(video)
    band = min(int(OUT_W * h / w), OUT_H)
    below_band = OUT_H - (OUT_H + band) // 2 - 130   # just under the picture
    return max(SAFE_BOTTOM, min(below_band, 900))


def frame_filter(video, start, end, post=""):
    """Filtergraph for one source range: per-shot crop / split / pad, ending in [v].

    `post` is appended to the finished frame (captions, punch-in, fps).
    """
    w, h, cw, ch, y = crop_geometry(video)
    shots = plan_shots(video, start, end)
    modes = [m for m in ("pad", "crop", "split") if any(x[2] == m for x in shots)]

    def pad(i, o):
        return (f"[{i}]split=2[{i}b][{i}f];"
                f"[{i}b]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,"
                f"crop={OUT_W}:{OUT_H},boxblur=40:3,eq=brightness=-0.32:saturation=0.6[{i}b2];"
                f"[{i}f]scale={OUT_W}:-2:flags=lanczos,unsharp=5:5:0.6:5:5:0.0[{i}f2];"
                f"[{i}b2][{i}f2]overlay=(W-w)/2:(H-h)/2,setsar=1[{o}]")

    def crop(i, o):
        return (f"[{i}]crop=w={cw}:h={ch}:x='{track_expr(shots, cw, w)}':y={y},"
                f"scale={OUT_W}:{OUT_H}:flags=lanczos,unsharp=5:5:0.7:5:5:0.0,setsar=1[{o}]")

    def split(i, o):
        # each speaker gets a 9:8 window (half of 9:16); positions held per shot
        hh = int(h * 0.62) // 2 * 2
        hw = min(w, int(hh * 9 / 8) // 2 * 2)
        def win(x, yy):
            return (max(0, min(int(x - hw / 2), w - hw)) // 2 * 2,
                    max(0, min(int(yy - hh * 0.42), h - hh)) // 2 * 2)
        sp = [x for x in shots if x[2] == "split"]
        xs = lambda k, j: expr_by_shot(sp, lambda q: win(*q[3][k])[j])
        return (f"[{i}]split=2[{i}t][{i}u];"
                f"[{i}t]crop={hw}:{hh}:x='{xs(0, 0)}':y='{xs(0, 1)}',scale={OUT_W}:{OUT_H // 2}[{i}t2];"
                f"[{i}u]crop={hw}:{hh}:x='{xs(1, 0)}':y='{xs(1, 1)}',scale={OUT_W}:{OUT_H // 2}[{i}u2];"
                f"[{i}t2][{i}u2]vstack,setsar=1[{o}]")

    build = {"pad": pad, "crop": crop, "split": split}
    if len(modes) == 1:
        vf = "[0:v]null[m0];" + build[modes[0]]("m0", "fr")
    else:
        names = [f"m{k}" for k in range(len(modes))]
        vf = f"[0:v]split={len(modes)}" + "".join(f"[{n}]" for n in names) + ";"
        vf += ";".join(build[m](n, f"{n}o") for m, n in zip(modes, names)) + ";"
        last = f"{names[0]}o"
        for k, (m, n) in enumerate(zip(modes[1:], names[1:]), 1):
            on = "+".join(f"between(t,{t0:.3f},{t1 - 0.001:.3f})"
                          for t0, t1, mm, _ in shots if mm == m)
            vf += f"[{last}][{n}o]overlay=0:0:enable='{on}'[l{k}];"
            last = f"l{k}"
        vf += f"[{last}]null[fr]"
    vf += f";[fr]null{post}[v]"
    label = modes[0] if len(modes) == 1 else "+".join(
        f"{m} {sum(1 for x in shots if x[2] == m)}" for m in modes)
    return vf, label


def post_text(path, title, tags):
    """`NN-name.txt` next to the clip: title and hashtags, ready to paste when posting."""
    tags = " ".join(t if t.startswith("#") else "#" + t for t in tags)
    path.with_suffix(".txt").write_text(f"{title}\n\n{tags}\n".lstrip(), encoding="utf-8")


def verify(path, expect):
    """Every rendered file: picture and sound the same length, and the length planned."""
    got = {}
    for line in sh([FFPROBE, "-v", "error", "-show_entries", "stream=codec_type,duration",
                    "-of", "csv=p=0", str(path)]).split():
        kind, _, d = line.partition(",")
        if d and d != "N/A":
            got[kind] = float(d)
    v, a = got.get("video", 0), got.get("audio", v if "audio" not in got else 0)
    problems = []
    if abs(v - a) > 0.15:
        problems.append(f"picture {v:.2f}s vs sound {a:.2f}s")
    if abs(v - expect) > 0.5:
        problems.append(f"length {v:.2f}s, planned {expect:.2f}s")
    if problems:
        print(f"   ! {path.name}: " + "; ".join(problems))
    return not problems


def expr_by_shot(shots, value):
    """Piecewise-constant expression: one value per shot, switched at its start."""
    expr = f"{value(shots[-1])}"
    for x in reversed(shots[:-1]):
        expr = f"if(lt(t,{x[1]:.3f}),{value(x)},{expr})"
    return expr


def render(video, words, clip, idx):
    start, end = clip["start"], clip["end"]
    out = OUT / f"{idx:02d}-{slug(clip['hook'] or clip['title'])}.mp4"

    sub = ROOT / f"cap_{idx}.ass"
    vf, clip["mode"] = frame_filter(video, start, end, "," + ass_filter(sub))
    captions(words, start, end, sub, caption_margin(video, clip["mode"]),
             headline=clip.get("headline", "") if HEADLINE else "")

    sh([FFMPEG, "-y", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{end-start:.3f}",
        "-i", str(video), "-filter_complex", vf,
        "-map", "[v]", "-map", "0:a?",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.12,"
               f"afade=t=out:st={max(0, end-start-0.15):.2f}:d=0.15",
        "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)])
    sub.unlink(missing_ok=True)
    verify(out, end - start)
    return out


def contact_sheet(clips):
    """One image with a frame from every clip, so review takes seconds."""
    tmp = ROOT / "sheet"
    tmp.mkdir(exist_ok=True)
    files = []
    for i, c in enumerate(clips, 1):
        p = tmp / f"{i:02d}.png"
        # most typical frame of the opening 4s, so fades to black never win
        sh([FFMPEG, "-y", "-v", "error", "-t", "4", "-i", str(c["file"]),
            "-frames:v", "1", "-vf", "thumbnail=n=48,scale=270:480", str(p)])
        files.append(str(p))
    cols = min(5, len(files))
    layout = "|".join(f"{(i % cols) * 270}_{(i // cols) * 480}" for i in range(len(files)))
    inputs = []
    for f in files:
        inputs += ["-i", f]
    out = OUT / "review.png"
    if len(files) == 1:
        Path(files[0]).replace(out)
        tmp.rmdir()
        return out
    filt = "".join(f"[{i}:v]" for i in range(len(files)))
    filt += f"xstack=inputs={len(files)}:layout={layout}:fill=black[o]"
    sh([FFMPEG, "-y", "-v", "error", *inputs, "-filter_complex", filt,
        "-map", "[o]", "-frames:v", "1", str(out)])
    for f in files:
        Path(f).unlink(missing_ok=True)
    tmp.rmdir()
    return out


def download(url):
    """Fetch the best copy up to 1080p — 720p crops to a blurry 404px strip."""
    IN.mkdir(exist_ok=True)
    print(f"   downloading {url}")
    t0 = time.time()
    sh([sys.executable, "-m", "yt_dlp", "--no-playlist", "--no-progress", "--windows-filenames",
        "-f", "bv*[height<=1080][ext=mp4][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", str(IN / "%(title).100s.%(ext)s"), url])
    # newest file, not the printed name: console encodings garble non-English titles
    new = [p for p in IN.glob("*.mp4") if p.stat().st_mtime >= t0 - 5]
    if not new:
        sys.exit("download finished but no .mp4 appeared in sources/")
    return max(new, key=lambda p: p.stat().st_mtime)


def pick_by_energy(video, total):
    """No speech to read (gameplay, sports, music, montage): pick by what you'd *feel* —
    loudness peaks and bursts of camera cuts — and start a beat before the peak."""
    import numpy as np
    raw = subprocess.run([FFMPEG, "-v", "error", "-i", str(video), "-ac", "1", "-ar", "8000",
                          "-f", "f32le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.float32)
    secs = int(total)
    if not len(a) or secs < MIN_S:
        return []
    rms = np.array([np.sqrt(np.mean(a[i*8000:(i+1)*8000] ** 2) + 1e-9) for i in range(secs)])
    loud = (rms - rms.mean()) / (rms.std() + 1e-9)
    cuts = np.zeros(secs)
    for c in shot_cuts(video, 0, total):
        if int(c) < secs:
            cuts[int(c)] += 1
    score = loud + 0.6 * cuts
    L = (MIN_S + MAX_S) // 2
    win = np.convolve(score, np.ones(L), "valid")
    picks = []
    for st in np.argsort(-win):
        st = float(st)
        peak = st + int(np.argmax(score[int(st):int(st) + L]))
        s0 = max(0.0, min(peak - L / 3, total - L))     # peak lands a third of the way in
        if any(s0 < p["end"] + GAP and s0 + L > p["start"] - GAP for p in picks):
            continue
        picks.append({"start": s0, "end": s0 + L, "hook": "", "title": f"moment at {int(s0//60)}:{int(s0%60):02d}",
                      "hashtags": [], "reason": "audio peak / fast cutting"})
        if len(picks) >= N_CLIPS:
            break
    return sorted(picks, key=lambda p: p["start"])


def profile(video, words, total):
    """What kind of video is this? Decides the mode when none is given."""
    w, h = frame_size(video)
    probe = min(total, 300)
    cpm = len(shot_cuts(video, 0, probe)) / max(probe / 60, 0.1)
    wpm = len(words) / max(total / 60, 0.1)
    if wpm < QUIET_WPM:
        mode = "visual"
    elif total <= 420 and cpm >= FASTCUT_CPM:
        mode = "reedit"
    else:
        mode = "clips"
    print(f"   profile: {w}x{h} · {wpm:.0f} words/min · {cpm:.0f} cuts/min · {LANG} → {mode}")
    if min(w, h) < 1000 and w > h:
        print(f"   ! source is {h}p — the 9:16 crop will look soft; a 1080p copy fixes it")
    return mode


def tune(total):
    """Short sources can't yield ten 30-second clips — scale the window."""
    global MIN_S, MAX_S, N_CLIPS
    if total >= 600:
        MIN_S, MAX_S = 22, 45
    elif total >= 300:
        MIN_S, MAX_S = 16, 38
    else:
        MIN_S, MAX_S = 10, 28
    room = int(total // (MIN_S + GAP))
    N_CLIPS = max(1, min(N_CLIPS, room))
    print(f"   window {MIN_S}-{MAX_S}s · up to {N_CLIPS} clips")


def check():
    """`--check`: is everything a run needs in place? Free (the NYO test lists models)."""
    ok = True
    def line(good, what, hint=""):
        nonlocal ok
        ok &= good
        print(f"  {'ok ' if good else 'NO '} {what}" + (f"  → {hint}" if hint and not good else ""))
    print(f"python {sys.version.split()[0]} · {sys.platform}")
    line(True, f"ffmpeg with captions: {FFMPEG}")
    line(Path(FFPROBE).exists() or shutil.which(FFPROBE) is not None, f"ffprobe: {FFPROBE}",
         "install ffmpeg (it includes ffprobe)")
    line((FONTS / "Montserrat-Black.ttf").exists(), "caption font", "pipeline/fonts is missing")
    line((MODELS_DIR / "yunet.onnx").exists(), "face model", "pipeline/models/yunet.onnx is missing")
    for mod in ("faster_whisper", "cv2", "numpy", "yt_dlp"):
        try:
            __import__(mod)
            line(True, f"python package {mod}")
        except ImportError:
            line(False, f"python package {mod}", "run the setup script again")
    line(SKILL.exists() and bool(editorial_rules()), "editorial rules (.agents/skills/clipping)")
    try:
        key = api_key()
    except SystemExit as e:
        line(False, "NYO key", str(e))
        key = None
    if key:
        r = requests.get(API.rsplit("/chat", 1)[0] + "/models", timeout=30,
                         headers={"Authorization": f"Bearer {key}"})
        names = [m.get("id") for m in r.json().get("data", [])] if r.ok else []
        line(r.ok, f"NYO key works ({len(names)} models)", f"HTTP {r.status_code}: check the key")
        if r.ok:
            line(MODEL in names, f"model {MODEL} available", "pick another in FALLBACK")
    print("\nready" if ok else "\nfix the NO lines above, then run --check again")
    return ok


def main():
    global OUT
    if "--check" in sys.argv[1:]:
        sys.exit(0 if check() else 1)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    forced = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--mode=")), None)
    global HEADLINE
    HEADLINE = HEADLINE or "--headline" in sys.argv[1:]
    arg = args[0] if args else None
    if arg and re.match(r"https?://", arg):
        video = download(arg)
    elif arg:
        video = Path(arg).expanduser().resolve()
    else:
        vids = sorted([p for p in IN.iterdir() if p.suffix.lower() in
                       (".mp4", ".mov", ".mkv", ".m4v", ".webm")], key=os.path.getmtime)
        if not vids:
            sys.exit(f"drop a video into {IN}")
        video = vids[-1]

    OUT = OUTROOT / video.stem
    OUT.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    total = duration(video)
    print(f"source: {video.name}  ({total/60:.1f} min)")
    tune(total)

    words, lines = transcribe(video)
    mode = forced or profile(video, words, total)
    if mode == "reedit":                  # trailer / promo: assemble, don't cut
        import reedit
        return reedit.run(video)
    picks = pick_by_energy(video, total) if mode == "visual" else pick_hooks(lines, words, total)
    if not picks:
        sys.exit("no usable clips")

    for old in list(OUT.glob("*.mp4")) + list(OUT.glob("[0-9][0-9]-*.txt")) + [OUT / "review.png"]:
        old.unlink(missing_ok=True)       # never mix two runs in one folder
    print(f"   rendering {len(picks)}...")
    for i, c in enumerate(picks, 1):
        c["file"] = render(video, words, c, i)
        print(f"   {i:02d}. {int(c['start']//60)}:{int(c['start']%60):02d} "
              f"({c['end']-c['start']:.0f}s) {c['hook'][:52]}")

    sheet = contact_sheet(picks)
    for c in picks:                       # ready-to-paste post text beside each clip
        post_text(c["file"], c.get("title", ""), c.get("hashtags", []))

    rows = "\n".join(
        f"| {c['file'].name} | {int(c['start']//60)}:{int(c['start']%60):02d} | "
        f"{c['end']-c['start']:.0f}s | {c.get('mode','')} | {c['title']} | {c['hook']} | "
        f"{' '.join(c['hashtags'])} | {c['reason']} |"
        for c in picks)
    (OUT / "report.md").write_text(
        f"# Clips — {video.name}\n\n"
        f"{len(picks)} clips · {total/60:.0f} min source · {mode} mode · {LANG} · "
        f"model `{USED['model'] or ('none' if mode == 'visual' else MODEL)}`\n\n"
        f"![review]({sheet.name})\n\n"
        f"| File | Start | Len | Mode | Title | Hook | Tags | Why |\n"
        f"|---|---|---|---|---|---|---|---|\n{rows}\n", encoding="utf-8")

    print(f"\ndone in {(time.time()-t0)/60:.1f} min → {OUT}")
    print(f"review sheet: {sheet}")


if __name__ == "__main__":
    main()
