---
name: clipping
description: "Run the clipper pipeline (any video or YouTube link to vertical captioned shorts) and apply its editorial rules: pick hooks, write titles, check clips before publishing."
version: 2.0.0
---

# Clipping

The pipeline lives in this repository (`pipeline/clips.py`, `pipeline/reedit.py`).
This file is its single source of editorial rules. The part between the `brief`
markers is sent to the AI on every run, so edit rules here, not in the code.
How it works in detail: `docs/HOW-IT-WORKS.md`. Change history: `CHANGELOG.md`.

## Running it

From the repository root. The Python inside the setup's virtual environment:

| | macOS / Linux | Windows |
|---|---|---|
| Python | `pipeline/.venv/bin/python` | `pipeline\.venv\Scripts\python.exe` |

```
<python> pipeline/clips.py "sources/<video>.mp4"     # or a YouTube link in quotes
<python> pipeline/clips.py "<video>" --mode=reedit   # force clips | reedit | visual
<python> pipeline/clips.py "<video>" --headline      # hook text at the top of normal clips
<python> pipeline/clips.py --check                   # test the setup (free)
<python> pipeline/check_captions.py "<video>"        # measure caption sync
```

- Sources go in `sources/`. Results land in `output/<video name>/`: clips,
  a `.txt` post text per clip, `report.md`, `review.png`, and `reedit/` for
  re-edits. Each run clears that video's old clips.
- After a run, read `report.md` and look at real frames (extract one with
  ffmpeg) before saying a clip is good. Lines starting with `!` are problems.
- Cost: only the AI pick is paid, about 1-2 US cents a run (about 5 cents for
  a 3-hour video). Transcription runs locally and is cached.

## Which mode fits the video

The pipeline chooses automatically; override with `--mode=` when it is wrong.

- Talking video (talk, podcast, interview, vlog): `clips`, continuous moments.
- Trailer / promo / fast-cut edit: `reedit`. Lines go in a new order, hook →
  build → payoff, 30-45 s. Never rearrange lines into a claim the source does
  not make.
- No speech (gameplay, sports, music): `visual`, picked by loudness peaks and
  fast cutting.
- A 2-3 minute trailer honestly yields 3-5 shorts, not 10.

<!-- brief:start -->
## Hook selection

- The first two seconds decide the clip. Open on the strongest line available.
- Start on a complete sentence. Never mid-thought, never on a filler word
  (And, But, So, Like, Okay, Well, Now).
- Prefer, in order: a specific number, a contradiction of common belief, a
  concrete story beat, a question the viewer can't answer, a named consequence.
- Reject generic advice. "Work hard and believe in yourself" is not a hook.
- A clip must make sense with zero context. If it needs the previous sentence,
  it is not a clip.
- Spread across the source. Clustering three clips from one good minute is a
  sign the selection gave up.

## Length and pacing

- 22-45 seconds for talking-head content. Under 20 s usually cuts the payoff;
  over 50 s loses the scroll.
- End on the payoff, not after it. One beat of silence is enough.
- Never let a clip end mid-sentence.

## Titles and tags

- Title under 60 characters, states the claim rather than describing the video.
- Headline (on-screen hook text): at most 6 words, states the tension.
- 3 hashtags: one topic, one niche, one broad. No hashtag soup.
<!-- brief:end -->

## Captions

- Karaoke: up to 3 words per line; the spoken word turns amber and swells to
  120% exactly when it is said (eases in over 60 ms, the previous word eases
  out over 80 ms). Heavy font (Montserrat Black), thick outline.
- Nothing on screen during silence: a pause over 0.35 s ends the line.
- Word timings are snapped to the audio first. Raw transcriber timings are
  about 120 ms off and glue pauses onto words. Measure with `check_captions.py`.
- Keep text inside the middle 80% of the frame; the bottom ~420 px is covered
  by TikTok/Reels buttons.
- Face shots: lower third. Letterboxed shots: just under the picture, never on
  the source's own text or logo. Two stacked speakers: on the seam.
- Re-edits: a short headline at the top, no progress bar.
- Japanese / Chinese / Thai: no spaces between words; never open on a particle.

## Framing

- Vertical 1080x1920. Decide framing per camera shot, not per clip: one face →
  tracking crop; two people side by side → stacked; wide shot / title card /
  screen → shown whole over a dark blur. Never pan across a camera cut.
- Trust only confident faces; statues, posters and printed T-shirts fool
  detectors.
- Never black bars, never a squashed picture.

## Re-edit cuts

- Lines from different moments are joined with a 0.2 s cross-fade of picture
  and sound; hard jumps between unrelated lines feel like they come from nowhere.
- Lines less than 1.5 s apart in the source play straight through.
- A punch-in zoom only hides a jump inside the same camera shot.
- Every output is checked: picture and sound the same length as planned.

## Source quality

- Use the best copy, up to 1080p. A 720p source looks soft once cropped (the
  run prints a warning). Check with `yt-dlp -F "<link>"`.

## Campaign rules come first

- Each Whop Content Rewards campaign sets its own minimum length, hashtags,
  links and platforms. Set `MIN_S`/`MAX_S` in `pipeline/clips.py` (or `TARGET`
  in `pipeline/reedit.py`) from the brief before running. A clip that breaks
  the brief can be rejected.
- Turn on the platform's paid / branded-content disclosure for campaign clips.

## Before publishing

- Rights: do you own it, or does a campaign license cover it? A clip of
  someone else's footage is their copyright, not yours.
- No commercial music. Platform library audio only.
- If the clip could embarrass the subject out of context, it is not worth the
  account.

## Keeping records (every change)

1. Make the change on a git branch or commit before editing, so it can be undone.
2. Update `README.md` / `docs/` if behaviour or settings changed.
3. Update this skill if a rule or how-to changed.
4. Add a dated line to `CHANGELOG.md`, then commit and push.

Hermes users also log agent/profile changes in `~/.hermes/CONFIG-CHANGES.md`.
