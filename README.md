# clipper

Turn any video into vertical, captioned shorts for TikTok, Reels and YouTube Shorts: talks, podcasts, interviews, trailers, gameplay, or a YouTube link. Built for Whop Content Rewards clipping campaigns.

- **Finds the moments.** An AI (NYO `glm-5.3-flash`) reads the transcript and picks the strongest standalone moments. Every clip opens on a clean sentence and ends after one.
- **Frames them for a phone.** Per camera shot: follows a face, stacks two speakers, or shows wide shots whole over a dark blur.
- **Karaoke captions.** The spoken word lights up exactly when it is said (about 20 ms accuracy), and nothing shows while the speaker is silent.
- **Works on trailers too.** Fast-cut videos are re-edited into a new story (hook → build → payoff) with soft cross-fades.
- **Cheap.** Transcription and editing run on your computer for free. Only the AI pick is paid: about **1–2 US cents per video**.

It runs on **Windows, macOS and Linux**, either by itself or with an AI coding agent (**OpenCode**, **Hermes**, Claude Code, Codex). The agent reads the same rules either way.

---

## Setup

You need an **NYO API key** (from your NYO account) and about **3 GB of free disk** (the speech model is 1.6 GB, downloaded on first run).

### Easiest: let OpenCode do it

Clone the repository, open OpenCode in the folder, and paste the prompt from **[docs/OPENCODE.md](docs/OPENCODE.md)**. It installs everything, asks for your NYO key, and tests the setup.

### Or run the setup script yourself

**Windows** (PowerShell):
```powershell
git clone https://github.com/marcxxv/clipper.git
cd clipper
powershell -ExecutionPolicy Bypass -File setup\setup.ps1
```

**macOS / Linux**:
```bash
git clone https://github.com/marcxxv/clipper.git
cd clipper
bash setup/setup.sh
```

The script installs `uv` (the Python manager) and `ffmpeg` if they're missing, creates `pipeline/.venv`, installs the Python packages, and creates `.env`. **Put your key in `.env`:**

```
NYO_API_KEY=rk_live_...
```

Then test everything (free):

```
pipeline\.venv\Scripts\python.exe pipeline\clips.py --check      # Windows
pipeline/.venv/bin/python pipeline/clips.py --check              # macOS / Linux
```

All lines should say `ok`. Step-by-step details and troubleshooting: **[docs/SETUP.md](docs/SETUP.md)**.

---

## Use

Run from the repository folder (Windows shown; on macOS/Linux use `pipeline/.venv/bin/python` and `/`):

```powershell
$py = "pipeline\.venv\Scripts\python.exe"
& $py pipeline\clips.py "https://youtu.be/XXXXXXXXXXX"   # download (up to 1080p) and clip
& $py pipeline\clips.py "sources\My Talk.mp4"            # a file you put in sources\
& $py pipeline\clips.py                                  # the newest file in sources\
& $py pipeline\clips.py "sources\x.mp4" --mode=reedit    # force a mode: clips | reedit | visual
& $py pipeline\clips.py "sources\x.mp4" --headline       # add hook text at the top of normal clips
```

Or just ask your agent: *"clip this: https://youtu.be/…"*.

### What you get: `output/<video name>/`

| File | What it is |
|---|---|
| `01-<first words>.mp4` … | the clips, 1080×1920, ready to post |
| `01-<first words>.txt` … | title and hashtags, ready to paste |
| `report.md` | each clip's start, length, framing, title, real opening words, and why it was picked |
| `review.png` | one frame per clip, to check them all at a glance |
| `reedit/` | for trailers: shorts `A-`, `B-`, `C-`, their line order, and `compare.mp4` (old cut, then new) |

### The three modes (chosen automatically)

| Video | Mode | What happens |
|---|---|---|
| Talk, podcast, interview, vlog | `clips` | the strongest continuous moments, up to 10 |
| Trailer, promo, fast-cut edit (≤ 7 min) | `reedit` | best lines in a new order, 3 shorts of 30–45 s with cross-fades |
| Gameplay, sports, music | `visual` | moments picked by loudness peaks and fast cutting |

Languages: the language is detected automatically, and titles and hashtags come back in it. Japanese, Chinese and Thai are handled.

---

## Using it with an agent

| Agent | What it reads | Setup |
|---|---|---|
| **OpenCode** | `AGENTS.md` + the skill in `.agents/skills/clipping/` | [docs/OPENCODE.md](docs/OPENCODE.md) |
| **Hermes** | the same skill, linked into a `clipper` profile | [docs/HERMES.md](docs/HERMES.md) |
| Claude Code / Codex | `AGENTS.md` and `.agents/skills/` | nothing extra |
| No agent | — | the commands above |

There is only **one copy** of the rules (`.agents/skills/clipping/SKILL.md`). Every agent, and the pipeline itself, reads that file.

---

## Rules that matter

- **Rights:** only clip footage you own or that a campaign has licensed to you. Someone else's video is their copyright.
- **Campaign briefs:** each Whop campaign sets its own minimum length, hashtags and platforms. Set the clip length to match (see [docs/HOW-IT-WORKS.md](docs/HOW-IT-WORKS.md#settings)).
- **Disclosure:** turn on the platform's paid / branded-content label for campaign clips.
- Your videos (`sources/`, `output/`) and your key (`.env`) are never committed to git.

## Repository layout

```
clipper/
├── README.md                 this file
├── AGENTS.md                 rules for any AI agent working here
├── CHANGELOG.md              what changed, newest first
├── .agents/skills/clipping/  the clipping skill: editorial rules + how to run
├── pipeline/                 clips.py, reedit.py, check_captions.py, fonts/, models/, requirements.txt
├── setup/                    setup.ps1 (Windows), setup.sh (macOS / Linux)
├── integrations/             ready-made configs for OpenCode and Hermes
├── docs/                     SETUP, OPENCODE, HERMES, HOW-IT-WORKS
├── sources/                  your input videos (not committed)
└── output/                   results (not committed)
```

## Keeping it in sync

Changes are made here, committed, and pushed. Everyone else runs `git pull` to get them. When you change behaviour, update the skill, the docs and `CHANGELOG.md` in the same commit (see `AGENTS.md`).

Third-party parts and their licences: [THIRD-PARTY.md](THIRD-PARTY.md).
