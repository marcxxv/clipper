# How it works

## The pipeline

```
video or YouTube link
  → audio decoded, transcribed locally (faster-whisper large-v3-turbo, word timings)
  → word timings snapped to the audio
  → mode chosen: clips · reedit · visual
  → the AI picks moments (NYO glm-5.3-flash, fallbacks glm-5, qwen3-30b)
  → each pick snapped to clean sentences and checked
  → framing per camera shot, karaoke captions, loudness to -14 LUFS
  → clips + post text + report + contact sheet; every file checked
```

Transcripts are cached in `output/<video>/<video>.transcript.json`, so re-runs skip transcription and take 1–3 minutes. Transcription runs at about 3.5× real time on a laptop CPU: roughly 8 minutes for a 28-minute video.

## Choosing the mode

| Detected | Mode |
|---|---|
| under 40 words a minute | `visual` |
| 7 minutes or shorter and 12+ camera cuts a minute | `reedit` |
| anything else | `clips` |

The run prints what it decided, e.g. `profile: 1920x1080 · 129 words/min · 29 cuts/min · en → reedit`.

## Picking moments (`clips` mode)

- The AI reads the transcript one sentence per line, with timestamps, plus the editorial brief from the skill. It returns 15 candidates, strongest first.
- Each candidate is moved to the nearest clean sentence start (capitalised, not a filler like *And / So / Yeah*, not a Japanese or Chinese particle) and ends just after a sentence closes.
- Candidates that are too short or long, open badly, or overlap a stronger pick are dropped. If fewer than 10 survive, the AI is asked again for more (`ROUNDS`), told which parts are already used.
- Long videos are read in 40-minute windows, so a 3-hour podcast is 5 requests (about 5 cents).
- The report shows the **real** opening words of each clip, not what the AI claimed.

## Re-editing (`reedit` mode)

For trailers and promos, which are already fast edits, a continuous cut is just a 10-second fragment. Instead:

- Every sentence is numbered and tagged *face* or *wide*. The AI builds 3 shorts by choosing line numbers in a new order: a hook, 2–6 build lines, and a payoff. The story must stay honest to the source.
- Lines from different moments are joined with a **0.2 s cross-fade** of picture and sound. Lines less than 1.5 s apart in the source play straight through. A punch-in zoom is used only to hide a jump inside one camera shot.
- Each short gets a headline at the top; there's no progress bar.
- `compare.mp4` plays the old continuous cut, then the re-edit.

## Picking moments without speech (`visual` mode)

The audio is scored second by second for loudness, plus bursts of camera cuts. The strongest windows are chosen, with the peak placed a third of the way in. No AI request, so it's free.

## Framing (per camera shot)

Camera cuts are detected first, and each shot gets its own layout:

| Layout | When | What |
|---|---|---|
| crop | one face in most of the shot | a 9:16 window that follows the face, jumping (not panning) at cuts |
| split | two comparable faces, level, too far apart for one crop | both stacked top/bottom; captions on the seam |
| pad | no confident face (wide shot, b-roll, title card, screen recording) | the whole frame over a dark blurred copy; captions just under it |

Faces below 0.85 confidence are ignored, because statues and posters score 0.6–0.8.

## Captions

- Karaoke in Montserrat Black: up to 3 words per line. The spoken word eases to amber and 120% size over 60 ms, while the previous word eases back over 80 ms.
- A line ends at a sentence end or at any pause over 0.35 s, and the last word lingers only 0.1 s, so the screen is empty during silence.
- **Word timing.** Whisper's raw word timings glue pauses onto the next word (60% of real pauses were hidden in a test talk), and word starts are off by about 120 ms. `refine_timing` fixes both:
  1. it trims each word to the actual burst of voice inside it;
  2. where words run together, it moves the boundary to the loudness dip between them (within ±120 ms).

  In a test with known timings, the median start error fell from 119 ms to 21 ms. On a real talk, 0% of pauses show a caption, and lines appear within 20 ms of the voice.
- Measure any video: `python pipeline/check_captions.py "<video>"`.

## Checks on every file

- Picture and sound have the same length, and match the planned length (`verify`). A problem prints a line starting with `!`.
- A 720p source prints a warning: the crop is upscaled about 2.7× and looks soft.
- Loudness is normalised to about -14 LUFS, the level TikTok, Reels and Shorts expect.

## Settings

At the top of `pipeline/clips.py` (and `pipeline/reedit.py` where marked):

| Setting | Default | Meaning |
|---|---|---|
| `MODEL` / `FALLBACK` | glm-5.3-flash / glm-5, qwen3-30b | AI models, tried in order |
| `N_CLIPS` | 10 | clips per video (fewer for short sources) |
| `MIN_S` / `MAX_S` | 22 / 45 s | clip length; scaled down for sources under 10 min. **Set from the campaign brief.** |
| `ROUNDS` | 2 | ask the AI again if too few picks pass |
| `CHUNK_MIN` | 40 | long videos are read in windows this long |
| `QUIET_WPM` / `FASTCUT_CPM` | 40 / 12 | mode detection thresholds |
| `FACE_CONF` | 0.85 | face confidence needed |
| `SAFE_BOTTOM` | 420 px | keeps captions clear of TikTok/Reels buttons |
| `CAP_FONT` / `CAP_SIZE` / `CAP_POP` | Montserrat Black / 84 / 120 % | caption look |
| `EASE_IN` / `EASE_OUT` | 60 / 80 ms | highlight hand-off |
| `GROUP_GAP` / `HOLD` | 0.35 / 0.10 s | pause that clears a line / last-word linger |
| `DIP_WIN` | 12 (×10 ms) | how far a word boundary may move to a loudness dip |
| `HEADLINE` | off | hook text on normal clips (`--headline` per run) |
| `TARGET` (reedit) | 30–45 s | re-edit length |
| `XFADE` / `KEEP_GAP` (reedit) | 0.20 / 1.5 s | cross-fade / play-through gap |

Changing `TIMING` (a version label) makes cached transcripts re-snap their word timings without re-transcribing.

## Known limits

- In very fast speech, some highlights can still be up to ~0.1 s off. A dedicated alignment model would fix it, but the multilingual ones are licensed non-commercial only.
- A face printed on a T-shirt can be mistaken for a person.
- YouTube downloads warn about a missing "JavaScript runtime". Downloads still work; installing `deno` silences it.
