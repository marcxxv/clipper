#!/usr/bin/env bash
# Link a Hermes "clipper" profile to this repository (macOS / Linux).
# Safe to re-run. Nothing is copied: the profile points at the repo's skill and
# SOUL.md, so `git pull` updates the agent too.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/../.." && pwd -P)"
PROFILE="${HERMES_HOME:-$HOME/.hermes}/profiles/clipper"

command -v hermes >/dev/null || { echo "Hermes is not installed (https://hermes-agent.nousresearch.com)"; exit 1; }

if [ ! -d "$PROFILE" ]; then
  hermes profile create clipper --no-skills \
    --description "Turns videos into vertical captioned shorts with the clipper pipeline."
  sed "s|REPO_PATH|$REPO|" "$REPO/integrations/hermes/config.yaml.example" > "$PROFILE/config.yaml"
  echo "created profile clipper"
else
  echo "profile clipper exists — config.yaml left as is"
fi

link() {  # link <target> <link-path>: replace a file/dir with a symlink, keeping a backup
  if [ -e "$2" ] && [ ! -L "$2" ]; then mv "$2" "$2.bak-$(date +%Y%m%d)"; fi
  ln -sfn "$1" "$2"
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
echo "done — start it with: clipper chat"
