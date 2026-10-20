#!/usr/bin/env python3
"""check_captions.py — measure caption sync against the actual audio.

  silent-shown : share of real pauses (>= 0.4 s) during which a caption is on screen
  onset error  : how far each highlight starts from the voice onset (median / p90)

Usage: python3 check_captions.py "../sources/<video>.mp4"
"""
import json, sys
from pathlib import Path

import numpy as np
import clips as C


def main():
    video = Path(sys.argv[1]).resolve()
    C.OUT = C.OUTROOT / video.stem
    words, _ = C.transcribe(video)
    a = C._audio(video)
    n = len(a) // 160
    db = 20 * np.log10(np.sqrt(np.mean(a[:n * 160].reshape(n, 160) ** 2, axis=1)) + 1e-9)
    thr = np.median(db[db > np.percentile(db, 40)]) - 18
    voiced = db >= thr

    total = C.duration(video)
    tmp = C.ROOT / "check.ass"
    C.captions(words, 0, total, tmp)
    shown = np.zeros(n, bool)
    onsets = []
    for line in tmp.read_text(encoding="utf-8").splitlines():
        if not line.startswith("Dialogue: 0,"):
            continue
        f = line.split(",", 9)
        t = lambda x: sum(float(p) * m for p, m in zip(x.split(":"), (3600, 60, 1)))
        s, e = t(f[1]), t(f[2])
        shown[int(s * 100):int(e * 100)] = True
        onsets.append(s)
    tmp.unlink()

    # real pauses: runs of unvoiced frames >= 0.4 s, inside the spoken part
    pauses, run = [], 0
    for i, v in enumerate(voiced):
        run = run + 1 if not v else 0
        if run == 40:
            pauses.append(i - 39)
    pauses = [p for p in pauses if words[0]["s"] * 100 < p < words[-1]["e"] * 100]
    hit = sum(shown[p + 10:p + 30].mean() > 0.5 for p in pauses)  # middle of the pause

    # onset error, measured where it is unambiguous: the first word after a pause
    err = []
    for p in pauses:
        k = p + 40
        while k < n and not voiced[k]:
            k += 1
        first = min(onsets, key=lambda s: abs(s * 100 - k))
        if abs(first * 100 - k) < 100:
            err.append(abs(first * 100 - k) * 10)
    print(f"pauses >= 0.4 s: {len(pauses)} · caption still on screen in {hit} "
          f"({hit / max(len(pauses), 1):.0%})")
    if err:
        print(f"line appears vs voice after a pause: median {np.median(err):.0f} ms · "
              f"p90 {np.percentile(err, 90):.0f} ms")


if __name__ == "__main__":
    main()
