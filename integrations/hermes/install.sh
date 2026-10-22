#!/usr/bin/env bash
# Link a Hermes "clipper" profile to this repository (macOS / Linux).
# Safe to re-run. Nothing is copied: the profile points at the repo's skill and
# SOUL.md, so `git pull` updates the agent too.
set -euo pipefail
RETARGET=false
case "${1:-}" in
  "") ;;
  --retarget) RETARGET=true; shift ;;
  --help) echo "Usage: bash integrations/hermes/install.sh [--retarget]"; exit 0 ;;
  *) echo "Unknown option: $1" >&2; exit 2 ;;
esac
[ "$#" -eq 0 ] || { echo "Unexpected arguments" >&2; exit 2; }
# CDPATH can make `cd` print its destination, corrupting command substitution.
REPO="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd -P)"
CLIPPER_HERMES_ROOT="${HERMES_HOME:-$HOME/.hermes}"
CLIPPER_HERMES_ROOT="${CLIPPER_HERMES_ROOT%/}"
if [ "$(basename "$(dirname "$CLIPPER_HERMES_ROOT")")" = "profiles" ]; then
  CLIPPER_HERMES_ROOT="$(dirname "$(dirname "$CLIPPER_HERMES_ROOT")")"
fi
PROFILE="$CLIPPER_HERMES_ROOT/profiles/clipper"
BACKUP_STAMP="$(date +%Y%m%dT%H%M%S)-$$"
run_hermes() { HERMES_HOME="$CLIPPER_HERMES_ROOT" hermes "$@"; }

command -v hermes >/dev/null || { echo "Hermes is not installed (https://hermes-agent.nousresearch.com)"; exit 1; }

if [ ! -d "$PROFILE" ]; then
  run_hermes profile create clipper --no-skills \
    --description "Turns videos into vertical captioned shorts with the clipper pipeline."
  cp "$REPO/integrations/hermes/config.yaml.example" "$PROFILE/config.yaml"
  run_hermes -p clipper config set terminal.cwd "$REPO"
  echo "created profile clipper"
else
  if [ "$RETARGET" = false ]; then
    CURRENT_REPO="$(run_hermes -p clipper config get terminal.cwd)"
    if [ -d "$CURRENT_REPO" ]; then
      CURRENT_REPO="$(CDPATH= cd -- "$CURRENT_REPO" && pwd -P)"
    fi
    if [ "$CURRENT_REPO" != "$REPO" ]; then
      echo "Clipper already points to another checkout. No changes made." >&2
      echo "To switch deliberately, rerun this installer with --retarget." >&2
      exit 1
    fi
  fi
  # Retarget an existing profile too, without replacing its model or other settings.
  cp -p "$PROFILE/config.yaml" "$PROFILE/config.yaml.bak-$BACKUP_STAMP"
  run_hermes -p clipper config set terminal.cwd "$REPO"
fi

link() {  # link <target> <link-path>: replace a file/dir with a symlink, keeping a backup
  if [ -L "$2" ] && [ "$(readlink "$2")" = "$1" ]; then return; fi
  if [ -e "$2" ] || [ -L "$2" ]; then mv "$2" "$2.bak-$BACKUP_STAMP"; fi
  ln -s "$1" "$2"
}
mkdir -p "$PROFILE/skills/media"
link "$REPO/.agents/skills/clipping" "$PROFILE/skills/media/clipping"
link "$REPO/integrations/hermes/SOUL.md" "$PROFILE/SOUL.md"

# NYO key: copy from the repo .env if the profile has none
if ! grep -q '^HERMES_CUSTOM_NYOLAB_API_KEY=.' "$PROFILE/.env" 2>/dev/null; then
  KEY="$(grep -E '^NYO_API_KEY=.' "$REPO/.env" 2>/dev/null | head -1 | cut -d= -f2- || true)"
  if [ -n "$KEY" ]; then
    printf '\nHERMES_CUSTOM_NYOLAB_API_KEY=%s\n' "$KEY" >> "$PROFILE/.env"
    echo "NYO key copied into the profile"
  else
    echo "add HERMES_CUSTOM_NYOLAB_API_KEY=<key> to $PROFILE/.env"
  fi
fi
echo "done — start it with: hermes -p clipper"
