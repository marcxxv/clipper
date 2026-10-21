# Architecture

Two portrait diagrams, read from top to bottom. The pictures are generated from the `.d2` text files next to them, so they're easy to keep current. Numbered cards show the main flow; side-by-side cards show alternatives without crossing connectors.

## 1. How a video becomes clips

![pipeline](architecture/pipeline.svg)

| Colour | Meaning |
|---|---|
| white | shared processing stages |
| blue | local moment selection |
| amber | AI moment selection |
| green | deliverables |

Transcription and rendering run locally. Ranking uses paid AI frame review unless `--no-ai` is set in visual mode. The shared editorial brief, optional trend briefs and personal campaign settings are listed below the flow rather than connected by long arrows.

The seven stages map to the code:

| Stage | Code |
|---|---|
| 1 · Source | `download()` in `pipeline/clips.py` |
| 2 · Transcribe | `transcribe()`, `refine_timing()` |
| 3 · Choose a mode | `profile()` (or `--mode`) |
| 4 · Find the story | `pick_hooks()` + `_validate()`, `reedit.py`, `pick_by_energy()` |
| 5 · Rank | `score.category()` and `score.rank()` in `pipeline/score.py`; clips and visual modes only |
| 6 · Frame & finish | `frame_filter()`, `captions()`, `render()`, `verify()` |
| 7 · Review your output | `contact_sheet()`, `post_text()`, the report in `main()` |

Re-edits bypass ranking: they assemble lines into a new story, then render and verify each short. Their outputs live in `output/<video>/reedit/`, including `compare.mp4`; continuous clips get best-first numbering and `review.png`.

## 2. Who runs it, and how improvements travel

![collaboration](architecture/collaboration.svg)

Every agent reads the same rules (`AGENTS.md`, `.agents/skills/clipping/`). The owner's agent pushes straight to `main`. A collaborator's agent opens a pull request by itself for tested, general improvements. Every push and pull request runs the Windows + Linux checks. Owner pushes reach `main` before those checks complete; collaborator pull requests are merged after passing checks.

## Keeping the diagrams current

When a feature, step, mode or flow changes:

1. edit `docs/architecture/pipeline.d2` or `collaboration.d2` (plain text; syntax at https://d2lang.com);
2. run `bash docs/architecture/render.sh` to regenerate the `.svg` files;
3. commit both the `.d2` and the `.svg`.

The `checks` workflow re-renders the diagrams and **fails if an `.svg` doesn't match its `.d2`**, so a forgotten re-render can't slip through.

Install D2 to render: `brew install d2` (macOS), `winget install terrastruct.d2` (Windows), or https://d2lang.com/tour/install. The renderer is pinned to **v0.9.0** so everyone produces identical images.

Why D2: it lays diagrams out automatically with straight right-angle connectors, it's plain text that agents can edit, and the SVG renders on GitHub.
