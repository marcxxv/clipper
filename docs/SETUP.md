# Setup in detail

## What gets installed

| Thing | Why | Size |
|---|---|---|
| `uv` | installs Python 3.12 and the packages, without touching any other Python on the machine | ~30 MB |
| `ffmpeg` (with libass) | cuts and renders video, burns in captions | ~150 MB |
| Python packages (`pipeline/requirements.txt`) | speech recognition, face detection, downloads | ~400 MB in `pipeline/.venv` |
| Whisper `large-v3-turbo` | the speech model, downloaded automatically on the first run | 1.6 GB |

Nothing is installed system-wide except `uv` and `ffmpeg`. Delete the repository folder to remove everything else; the speech model sits in the Hugging Face cache (`~/.cache/huggingface`).

## Windows

1. Install **Git** if you don't have it: `winget install --id Git.Git -e`
2. Open **PowerShell** and run:
   ```powershell
   git clone https://github.com/marcxxv/clipper.git
   cd clipper
   powershell -ExecutionPolicy Bypass -File setup\setup.ps1
   ```
   The script:
   - installs `uv` (official installer) and `ffmpeg` (`winget install Gyan.FFmpeg`) if missing;
   - creates `pipeline\.venv` with Python 3.12 and installs the packages;
   - copies `.env.example` to `.env`;
   - runs the self-test.
3. Open `.env` in Notepad (`notepad .env`), put your key after `NYO_API_KEY=`, and save.
4. Test: `pipeline\.venv\Scripts\python.exe pipeline\clips.py --check`. Every line should say `ok`.

If `ffmpeg` was just installed and the check says it's missing, **close and reopen PowerShell**: Windows only picks up new programs in new windows.

## macOS

1. Install Homebrew if needed (https://brew.sh), then:
   ```bash
   git clone https://github.com/marcxxv/clipper.git
   cd clipper
   bash setup/setup.sh
   ```
   The script installs `uv` and `ffmpeg` (via Homebrew) if missing, creates `pipeline/.venv` and `.env`, and runs the self-test. Homebrew's standard `ffmpeg` has no caption support (libass), so the script also installs `ffmpeg-full`, which the pipeline finds automatically.
2. Put your key in `.env` (`open -e .env`).
3. Test: `pipeline/.venv/bin/python pipeline/clips.py --check`.

## Linux

Same as macOS. The script installs ffmpeg with `apt`, `dnf` or `pacman` if it finds one; otherwise install ffmpeg yourself first.

## The NYO key

The pipeline looks for the key in this order:
1. the environment variable `NYO_API_KEY` (or `HERMES_CUSTOM_NYOLAB_API_KEY`);
2. `.env` at the repository root;
3. a Hermes `clipper` profile's `.env`.

`.env` is in `.gitignore`, so the key never goes to GitHub.

## Updating

```
git pull
```
then run the setup script again if `pipeline/requirements.txt` changed. It's safe to re-run at any time.

## Troubleshooting

| Problem | Fix |
|---|---|
| `no ffmpeg with libass found` | install a full ffmpeg build (Windows: `winget install Gyan.FFmpeg`; macOS: `brew install ffmpeg`), reopen the terminal. To use a specific one: set `CLIPS_FFMPEG` to its full path |
| `no NYO key` | put `NYO_API_KEY=...` in `.env` at the repo root |
| `NO NYO key works (HTTP 401)` | the key is wrong or expired |
| first run sits at "transcribing" for long | normal: the 1.6 GB speech model downloads once, then transcription runs at ~3.5× real time |
| `! … picture … vs sound` | a render problem; re-run, and report it if it repeats |
| YouTube warning about a "JavaScript runtime" | harmless for now; `winget install DenoLand.Deno` / `brew install deno` silences it |
| scripts blocked on Windows | run them with `powershell -ExecutionPolicy Bypass -File …` as shown |
