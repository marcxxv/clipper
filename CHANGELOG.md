# Changelog

Newest first. Every change to code, settings, rules or docs gets a dated entry here
(see `AGENTS.md`).

## 2026-10-21 — architecture diagrams
- `docs/ARCHITECTURE.md` with two D2 diagrams (pipeline; people, agents and GitHub flow),
  shown in the README. Sources in `docs/architecture/*.d2`, rendered by `render.sh`
  (D2 v0.9.0). CI fails if a diagram image is out of date.

## 2026-10-21 — hook scoring, trends, automatic git workflow
- `score.py`: every candidate's first 3 s scored on voice (energy, pitch variation, pace,
  dead air), picture (face, motion, cuts) and an AI look at the phone-cropped frames
  (NYO glm-5.3-flash, which accepts images), weighted by detected content category.
  Clips numbered best-first; scores and strengths in the report. `--category=` override.
- `trends.py`: measures the most-viewed Shorts of channels (`@name`) or hashtags; writes
  `trends/<name>.md`; `clips.py --trend=<name>` adds that brief to the AI's instructions.
- `settings.local.json` (git-ignored) for personal values such as campaign lengths.
- `--no-ai` offline mode and `CLIPS_WHISPER` model override; `ROUNDS` 2 → 3.
- GitHub: `main` protected (pull requests required, owner bypasses); `checks` workflow
  installs and runs an offline clip on Windows and Linux for every push and PR.
- `AGENTS.md`: owner's agent pushes automatically; a collaborator's agent opens pull
  requests by itself for tested, general improvements.
- Windows setup falls back to Chocolatey when winget is missing.

## 2026-10-21 — published as a repository
- Repository layout: one skill at `.agents/skills/clipping/` (read by OpenCode, Hermes,
  Claude Code, Codex and the pipeline itself); setup scripts for Windows and macOS/Linux;
  OpenCode and Hermes integrations; docs split into SETUP, OPENCODE, HERMES, HOW-IT-WORKS.
- Windows support: UTF-8 file handling, relative caption paths (a drive letter breaks
  ffmpeg filters), ffmpeg/ffprobe found on PATH, downloads robust to non-English titles.
- `clips.py --check` self-test (ffmpeg, fonts, face model, packages, NYO key and model).
- NYO key read from `NYO_API_KEY` or the repo's `.env` as well as a Hermes profile.
- Only the skill's editorial brief (between `brief` markers) is sent to the AI: about
  1,100 characters instead of 3,000 per request.

## 2026-10-21 — posting helpers
- A `.txt` beside every clip and re-edit with title and hashtags, ready to paste.
- Optional `--headline`: AI hook text at the top of normal clips (off by default).

## 2026-10-21 — captions and re-edits
- Karaoke captions: the spoken word eases to amber and 120% as it is said; Montserrat Black.
- Word timings snapped to the audio: start error 119 → 21 ms median (ground-truth test);
  no caption during pauses (was shown in 60% of pauses).
- Re-edits: 0.2 s cross-fades of picture and sound; nearby lines play through; punch-in
  only for same-shot jumps; progress bar removed.
- Fixed: re-edit picture stopping early (one-frame offset). Every file is now checked for
  picture/sound length.
- Japanese/Chinese: phrase breaks as sentence ends, never open on a particle; hyphenated
  words re-joined.

## 2026-10-20 — modes for every video type
- Auto mode: `clips` (talk), `reedit` (trailer), `visual` (no speech); `--mode=` override.
- Per-shot framing: face crop, two-speaker split, padded wide shots.
- Clips start and end on real sentences; overlap and ranking fixed; second AI round.
- Language-aware text, long videos read in 40-minute windows, YouTube link input.
