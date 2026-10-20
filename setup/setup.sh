#!/usr/bin/env bash
# clipper setup for macOS / Linux. Safe to re-run.
#   bash setup/setup.sh
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$(pwd -P)"
say() { printf '\n== %s\n' "$*"; }

say "uv (Python manager)"
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
uv --version

say "ffmpeg (with libass, for captions)"
has_libass() { local f; f="$(ffmpeg -hide_banner -filters 2>/dev/null || true)"; [[ "$f" =~ \ (ass|subtitles)\  ]]; }
if ! command -v ffmpeg >/dev/null || ! has_libass; then
  if command -v brew >/dev/null; then
    # Homebrew's slim "ffmpeg" may lack libass; "ffmpeg-full" has it
    brew install ffmpeg; has_libass || brew install ffmpeg-full
  elif command -v apt-get >/dev/null; then sudo apt-get update && sudo apt-get install -y ffmpeg
  elif command -v dnf >/dev/null; then sudo dnf install -y ffmpeg
  elif command -v pacman >/dev/null; then sudo pacman -S --noconfirm ffmpeg
  else echo "Install ffmpeg (with libass) yourself, then re-run."; exit 1
  fi
fi
ffmpeg -hide_banner -version | sed -n 1p   # the pipeline picks whichever build has libass

say "Python 3.12 environment in pipeline/.venv"
uv venv --allow-existing --python 3.12 pipeline/.venv
uv pip install --python pipeline/.venv/bin/python -r pipeline/requirements.txt

say ".env"
if [ ! -f .env ]; then cp .env.example .env; echo "created .env — put your NYO_API_KEY in it"; else echo ".env exists"; fi

say "self-test"
pipeline/.venv/bin/python pipeline/clips.py --check || {
  echo; echo "Fix the NO lines (usually: put NYO_API_KEY in $REPO/.env), then run:"
  echo "  pipeline/.venv/bin/python pipeline/clips.py --check"
}
