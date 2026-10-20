#!/usr/bin/env python3
"""trends.py — learn what the most-viewed Shorts on a topic do in their first seconds.

  python pipeline/trends.py "@JordanBPeterson, @ChrisWillx"   # channels (best: on-topic)
  python pipeline/trends.py "stoicism, mindset"                # hashtags (noisier)
  python pipeline/clips.py "<video>" --trend=jordanbpeterson-chriswillx

Finds the most-viewed YouTube Shorts from those channels / hashtag pages, downloads only their first
SNIP_S seconds (deleted after measuring), and measures the same signals the scorer
uses: opening line, voice energy / pitch / pace, dead air, face size, motion, cuts.
The resulting brief (example hooks, typical length and pace) is added to the AI's
instructions when you pass --trend=. Free: no AI requests, nothing reposted.
"""

import json, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from statistics import median

import clips as C
import score

N_DEFAULT = 12            # Shorts analysed
SNIP_S    = 8             # seconds downloaded from each
TRENDS    = C.REPO / "trends"


def slugify(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:60] or "topic"


def search(topic, want):
    """Most-viewed Shorts from each hashtag's Shorts page (YouTube search barely
    returns Shorts; hashtag pages list them with view counts)."""
    seen = {}
    for item in filter(None, (t.strip() for t in topic.split(","))):
        if item.startswith("@"):                       # a channel: its Shorts are on-topic
            tag, url = item, f"https://www.youtube.com/{item}/shorts"
        else:                                          # a hashtag: popular but noisy
            tag = "#" + re.sub(r"[^\w]", "", item.lower())
            url = f"https://www.youtube.com/hashtag/{tag[1:]}/shorts"
        r = subprocess.run([sys.executable, "-m", "yt_dlp", "--flat-playlist", "-J",
                            "--playlist-end", "80", url], capture_output=True,
                           encoding="utf-8", errors="replace")
        try:
            entries = json.loads(r.stdout).get("entries", [])
        except ValueError:
            entries = []
        print(f"   {tag}: {len(entries)} Shorts")
        for e in entries:
            if e.get("id") and e.get("view_count"):
                seen[e["id"]] = {"id": e["id"], "title": e.get("title") or "",
                                 "views": int(e["view_count"]), "secs": 0.0,
                                 "url": f"https://www.youtube.com/shorts/{e['id']}"}
    return sorted(seen.values(), key=lambda r: -r["views"])[:want]


def measure(row, tmp, model):
    """First SNIP_S seconds: opening line + hook signals. Returns None if unusable."""
    f = tmp / f"{row['id']}.mp4"
    r = subprocess.run([sys.executable, "-m", "yt_dlp", "-q", "--no-warnings", "--no-simulate",
                        "--print", "before_dl:%(duration)s",
                        "-f", "bv*[height<=480]+ba/b[height<=480]/b", "--merge-output-format", "mp4",
                        "--download-sections", f"*0-{SNIP_S}", "-o", str(f), row["url"]],
                       capture_output=True, encoding="utf-8", errors="replace", cwd=tmp)
    if not f.exists():
        return None
    try:
        row["secs"] = float(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        pass
    audio = C._audio(f)
    segs, info = model.transcribe(audio, word_timestamps=True, vad_filter=True)
    C.set_lang(info.language)
    words = [{"w": w.word.strip(), "s": float(w.start), "e": float(w.end)}
             for s in segs for w in (s.words or [])]
    words = C.refine_timing(words, audio) if words else []
    hook = C.joined([w for w in words if w["s"] < score.HOOK_S + 1.5])
    sig = score.voice(audio, words, 0, score.HOOK_S)
    sig.update(score.picture(f, 0, score.HOOK_S, C.frame_size(f)))
    f.unlink(missing_ok=True)
    return dict(row, hook=hook, lang=C.LANG, **{k: round(v, 3) for k, v in sig.items()})


def write(topic, rows):
    TRENDS.mkdir(exist_ok=True)
    talk = [r for r in rows if r["rate"] > 0.5]
    base = talk if len(talk) >= 4 else rows          # speech stats from Shorts that talk
    med = lambda k: round(median(r[k] for r in base), 2)
    lines = "\n".join(
        f"| {r['views']:,} | {r['secs']:.0f}s | {r['rate']:.1f} | {r['pitch']:.1f} | "
        f"{r['dead']:.1f} | {r['face']:.3f} | {r['motion']:.1f} | {int(r['cuts'])} | "
        f"{r['hook'][:70].replace('|', '/')} |" for r in rows)
    hooks = "\n".join(f"- \"{r['hook'][:110]}\" ({r['views']:,} views)" for r in talk[:8])
    brief = (f"## What is winning now: {topic}\n\n"
             f"The {len(rows)} most-viewed Shorts on this topic (measured {time.strftime('%Y-%m-%d')}):\n"
             + (f"- talking Shorts: typical length {med('secs'):.0f} s; in the first "
                f"{score.HOOK_S:.0f} s they speak {med('rate'):.1f} words/s with "
                f"{med('dead'):.1f} s of dead air\n" if len(talk) >= 4 else
                "- too few talking Shorts here to give speech numbers\n")
             + f"- {sum(r['face'] > 0.02 for r in rows)} of {len(rows)} open on a visible face; "
             f"{len(talk)} of {len(rows)} open with speech"
             + (" (this tag is mostly music/visual: use a narrower tag for talking clips)"
                if len(talk) < len(rows) / 2 else "") + "\n"
             + (f"- opening lines that worked:\n{hooks}\n" if hooks else "")
             + "Prefer moments whose opening works the same way. Do not copy these lines.")
    path = TRENDS / f"{slugify(topic)}.md"
    path.write_text(
        f"# Trends: {topic}\n\n"
        f"Generated by `pipeline/trends.py`. Use with `clips.py \"<video>\" --trend={path.stem}`.\n"
        f"Only the block between the markers is sent to the AI.\n\n"
        f"<!-- brief:start -->\n{brief}\n<!-- brief:end -->\n\n"
        f"## Medians (first {score.HOOK_S:.0f} s)\n\n"
        f"| length | words/s | pitch var | dead air | face share | motion | cuts |\n|---|---|---|---|---|---|---|\n"
        f"| {med('secs')} s | {med('rate')} | {med('pitch')} | {med('dead')} s | "
        f"{med('face')} | {med('motion')} | {med('cuts')} |\n\n"
        f"## Shorts measured\n\n"
        f"| views | length | words/s | pitch var | dead air | face | motion | cuts | opening |\n"
        f"|---|---|---|---|---|---|---|---|---|\n{lines}\n", encoding="utf-8")
    return path


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit('usage: python pipeline/trends.py "<topic>" [--n=12]')
    n = next((int(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--n=")), N_DEFAULT)
    topic = args[0]
    print(f"trends: {topic}")
    rows = search(topic, n)
    if not rows:
        sys.exit("no Shorts found for that topic")
    print(f"   {len(rows)} Shorts, {rows[-1]['views']:,} to {rows[0]['views']:,} views; measuring first {SNIP_S}s of each...")
    from faster_whisper import WhisperModel
    model = WhisperModel(C.WHISPER, device="cpu", compute_type="int8")
    tmp = Path(tempfile.mkdtemp(prefix="clipper-trends-"))
    done = []
    try:
        for i, r in enumerate(rows, 1):
            m = measure(r, tmp, model)
            print(f"   {i:2d}. {r['views']:>12,}  " + (f"{m['hook'][:60]}" if m else "(skipped)"))
            if m:
                done.append(m)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if not done:
        sys.exit("could not measure any Short")
    print(f"\nwrote {write(topic, done)}")


if __name__ == "__main__":
    main()
