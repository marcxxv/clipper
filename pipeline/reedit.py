#!/usr/bin/env python3
"""reedit.py — re-cut a short, fast-cut source (trailer, promo) into story shorts.

clips.py cuts one continuous piece. That fails on trailers: they are already an
edit, so a continuous piece is a 10-second fragment. This assembles one instead:

  numbered sentences (+ face/wide tag per line) → model picks sentence ids in a
  new order: hook → build → payoff → each line framed per shot → joined with short
  cross-fades (picture and sound), punch-in only to hide a same-shot jump →
  karaoke captions (shared with clips.py), headline, loudness. No progress bar.

Usage:  python3 reedit.py "../sources/<video>.mp4"
Output: output/<video>/reedit/  (A-, B-, C-*.mp4, report.md, compare.mp4)
"""

import json, re, subprocess, sys, time
from pathlib import Path

import clips as C

N_EDITS    = 3            # different shorts asked for
TARGET     = (30, 45)     # seconds per short
PUNCH      = 1.08         # punch-in that hides a jump inside one camera shot
LEAD, TAIL = 0.15, 0.40   # breathing room around each sentence (eaten partly by the fade)
XFADE      = 0.20         # cross-fade between lines from different moments
CUT        = 0.04         # near-hard cut for a jump inside the same shot
SAME_SHOT  = 8.0          # lines this close in the source, with no camera cut, share a shot
KEEP_GAP   = 1.5          # back-to-back lines closer than this play straight through
FPS        = 30


# ---------------- story picking ----------------

def numbered(video, words):
    """Sentences with timing and whether a face is on screen."""
    out = []
    for s, text, e in C.sentences(words):
        shots = C.plan_shots(video, s, e)
        face = sum(t1 - t0 for t0, t1, m, _ in shots if m == "crop") / max(e - s, 0.01)
        out.append({"id": len(out), "s": s, "e": e, "text": text,
                     "look": "face" if face >= 0.5 else "wide"})
    return out


def _prompt(lines, total):
    listing = "\n".join(f"{l['id']:>3} | {l['s']:6.1f}s | {l['e']-l['s']:4.1f}s | "
                        f"{l['look']:4} | {l['text']}" for l in lines)
    return (
        f"You are a trailer editor re-cutting a {total:.0f}-second video into vertical shorts.\n\n"
        f"Build {N_EDITS} different shorts by choosing numbered lines and putting them in a NEW order.\n"
        "Structure each one as a story:\n"
        "- HOOK (first line): makes sense alone and stops the scroll in 2 seconds — a question,\n"
        "  a contradiction, a bold claim. Never a line that needs earlier context (he, that, it).\n"
        "- BUILD (2-6 lines): context and escalation, each line raising the stakes.\n"
        "- PAYOFF (last line): the line that lands. The viewer should feel the arc closed.\n\n"
        f"- Total spoken length {TARGET[0]}-{TARGET[1]} seconds (sum of the length column).\n"
        "- Prefer 'face' lines; a 'wide' line is fine for a beat, not for the hook.\n"
        "- Each short gets a different hook. Reuse a line across shorts only if essential.\n"
        "- The story must be honest: never reorder lines into a claim the source does not make.\n"
        f"- Write headline, title and hashtags in the source's own language ({C.LANG}).\n\n"
        + (C.editorial_rules() + "\n\n")
        + "Return ONLY JSON, no prose, no code fences:\n"
        '[{"ids": [7, 2, 3, 11, 19], "headline": "on-screen top text, max 6 words",\n'
        '  "title": "post title under 60 characters", "hashtags": ["#one", "#two", "#three"],\n'
        '  "why": "the arc in max 12 words"}]\n\n'
        "Lines (id | start | length | look | text):\n" + listing
    )


def _opens_clean(line):
    first = (line["text"].split() or [""])[0][:12]
    return bool(first) and C._capital({"w": first}) and not C._bad_start({"w": first})


def pick_edits(lines, total):
    raw = C._ask(_prompt(lines, total), N_EDITS)
    edits = []
    for r in raw:
        try:
            ids = [int(i) for i in r["ids"]]
        except (KeyError, TypeError, ValueError):
            continue
        ids = [i for n, i in enumerate(ids) if 0 <= i < len(lines) and i not in ids[:n]]
        while ids and not _opens_clean(lines[ids[0]]):   # hook must open clean
            ids.pop(0)
        while len(ids) > 2 and length(lines, ids) > TARGET[1] + 2:
            ids.pop(len(ids) // 2)                         # trim the build, keep hook + payoff
        if len(ids) < 3 or length(lines, ids) < TARGET[0] - 10:
            continue
        edits.append({"ids": ids, "headline": r.get("headline", "")[:48],
                      "title": r.get("title", ""), "hashtags": r.get("hashtags", [])[:3],
                      "why": r.get("why", "")})
    return edits


def length(lines, ids):
    return sum(lines[i]["e"] - lines[i]["s"] + LEAD + TAIL for i in ids)


# ---------------- assembly ----------------

def segments(lines, ids, words):
    """Source ranges in play order; lines that follow on in the source stay one piece."""
    segs = []
    for i in ids:
        l = lines[i]
        prev = max((w["e"] for w in words if w["e"] <= l["s"]), default=0)
        nxt = min((w["s"] for w in words if w["s"] >= l["e"]), default=l["e"] + 1)
        a, b = max(prev, l["s"] - LEAD), min(nxt, l["e"] + TAIL)
        if segs and segs[-1][2] == i - 1 and abs(segs[-1][1] - a) < KEEP_GAP:
            segs[-1] = (segs[-1][0], b, i)
        else:
            segs.append((a, b, i))
    return [(a, b) for a, b, _ in segs]


def frame(video, a, b, punch, modes):
    zoom = f",crop=iw/{PUNCH}:ih/{PUNCH},scale={C.OUT_W}:{C.OUT_H}:flags=lanczos" if punch else ""
    vf, label = C.frame_filter(video, a, b, f"{zoom},fps={FPS}")
    modes.append(label)
    return vf


def video_len(p):
    out = C.sh([C.FFPROBE, "-v", "error", "-select_streams", "v", "-count_packets",
                "-show_entries", "stream=nb_read_packets", "-of", "csv=p=0", str(p)])
    return int(out.strip()) / FPS


def same_shot(video, prev, a):
    """Next line comes shortly after the last one in the same camera shot: a jump cut."""
    return 0 < a - prev < SAME_SHOT and not C.shot_cuts(video, prev, a)


def render_edit(video, words, segs, edit, tag, work):
    parts, timeline, at, modes, joins = [], [], 0.0, [], []
    punched = False
    for n, (a, b) in enumerate(segs):
        jump = n > 0 and same_shot(video, segs[n - 1][1], a)
        punched = (not punched) if jump else False        # alternate only across jumps
        p = work / f"{tag}{n:02d}.mp4"
        C.sh([C.FFMPEG, "-y", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}",
              "-i", str(video), "-filter_complex", frame(video, a, b, punched, modes),
              "-map", "[v]", "-map", "0:a?", "-ar", "48000", "-ac", "2",
              "-c:v", "libx264", "-crf", "17", "-preset", "veryfast",
              "-c:a", "aac", "-b:a", "192k", str(p)])
        d = video_len(p)                        # picture length, after frame rounding
        if n:
            joins.append(CUT if jump else XFADE)
            at -= joins[-1]                     # the fade overlaps the two lines
        timeline += [dict(w, s=at + w["s"] - a, e=at + min(w["e"], b) - a)
                     for w in words if a <= w["s"] < b]
        parts.append((p, d))
        at += d

    # one pass: chain xfade (picture) and acrossfade (sound) over every join
    # every piece restarts its clock at 0 and its sound is cut to its picture,
    # otherwise a one-frame offset makes xfade silently drop the rest of the video
    fg, v, au, off = [], "0v", "0a", 0.0
    for k, (p, d) in enumerate(parts):
        fg.append(f"[{k}:v]setpts=PTS-STARTPTS,settb=AVTB,fps={FPS},format=yuv420p[{k}v]")
        fg.append(f"[{k}:a]asetpts=PTS-STARTPTS,aresample=48000,apad,atrim=0:{d:.3f}[{k}a]")
    for k in range(1, len(parts)):
        off += parts[k - 1][1] - joins[k - 1]
        fg.append(f"[{v}][{k}v]xfade=transition=fade:duration={joins[k-1]:.2f}:offset={off:.3f}[x{k}]")
        fg.append(f"[{au}][{k}a]acrossfade=d={joins[k-1]:.2f}[y{k}]")
        v, au = f"x{k}", f"y{k}"

    sub = work / f"{tag}.ass"
    C.captions(timeline, 0, at, sub, C.caption_margin(video, " ".join(modes)),
               headline=edit["headline"])
    fg.append(f"[{v}]{C.ass_filter(sub)}[v]")
    fg.append(f"[{au}]loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=in:d=0.08,"
              f"afade=t=out:st={max(0, at - 0.2):.3f}:d=0.2[a]")
    out = C.OUT / "reedit" / f"{tag}-{C.slug(edit['title'] or edit['headline'])}.mp4"
    inputs = [x for p, _ in parts for x in ("-i", str(p))]
    C.sh([C.FFMPEG, "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fg),
          "-map", "[v]", "-map", "[a]",
          "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
          "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out)])
    for p, _ in parts:
        p.unlink(missing_ok=True)
    sub.unlink(missing_ok=True)
    C.verify(out, at)
    return out, at


# ---------------- before / after ----------------

def compare(before, after, out):
    """Old continuous cut, then the new assembled short, back to back."""
    C.sh([C.FFMPEG, "-y", "-v", "error", "-i", str(before), "-i", str(after),
          "-filter_complex",
          f"[0:v]fps={FPS},setsar=1[a];[1:v]fps={FPS},setsar=1[b];"
          "[0:a]aresample=48000[x];[1:a]aresample=48000[y];"
          "[a][x][b][y]concat=n=2:v=1:a=1[v][o]",
          "-map", "[v]", "-map", "[o]", "-c:v", "libx264", "-crf", "22",
          "-preset", "veryfast", "-c:a", "aac", "-b:a", "128k",
          "-movflags", "+faststart", str(out)])


def main():
    if len(sys.argv) < 2:
        sys.exit('usage: python3 reedit.py "../sources/<video>.mp4"')
    run(Path(sys.argv[1]).expanduser().resolve())


def run(video):
    C.apply_local(globals())                     # e.g. {"TARGET": [45, 60]}
    C.OUT = C.OUTROOT / video.stem
    dest = C.OUT / "reedit"
    dest.mkdir(parents=True, exist_ok=True)
    for old in list(dest.glob("*.mp4")) + list(dest.glob("*.txt")):
        old.unlink()

    t0 = time.time()
    total = C.duration(video)
    print(f"source: {video.name}  ({total:.0f}s) — re-edit mode")
    words, _ = C.transcribe(video)
    print("   tagging lines (face / wide)...")
    lines = numbered(video, words)
    edits = pick_edits(lines, total)
    if not edits:
        sys.exit("model returned no usable edit")

    work = C.ROOT / "reedit_tmp"
    work.mkdir(exist_ok=True)
    rows = []
    for edit, tag in zip(edits, "ABCDE"):
        segs = segments(lines, edit["ids"], words)
        out, secs = render_edit(video, words, segs, edit, tag, work)
        edit["file"], edit["secs"] = out, secs
        C.post_text(out, edit["title"], edit["hashtags"])
        story = " / ".join(lines[i]["text"] for i in edit["ids"])
        print(f"   {tag}. {secs:4.1f}s  {len(segs)} cuts  {edit['headline']}")
        rows.append(f"## {tag} — {edit['title']}\n\n"
                    f"`{out.name}` · {secs:.0f}s · {len(segs)} cuts · "
                    f"{' '.join(edit['hashtags'])}\n\n"
                    f"**Headline:** {edit['headline']}  \n**Arc:** {edit['why']}\n\n"
                    + "\n".join(f"{n + 1}. `{lines[i]['s']:.0f}s` {lines[i]['text']}"
                                for n, i in enumerate(edit["ids"])) + "\n")
    work.rmdir()

    befores = sorted(C.OUT.glob("01-*.mp4"))
    if befores:
        compare(befores[0], edits[0]["file"], dest / "compare.mp4")
        print(f"   compare.mp4: {befores[0].name} (before) then {edits[0]['file'].name} (after)")

    (dest / "report.md").write_text(
        f"# Re-edits — {video.name}\n\n{len(edits)} shorts · model `{C.USED['model']}` · "
        "lines re-ordered into hook → build → payoff\n\n" + "\n".join(rows), encoding="utf-8")
    print(f"\ndone in {(time.time() - t0) / 60:.1f} min → {dest}")


if __name__ == "__main__":
    main()
