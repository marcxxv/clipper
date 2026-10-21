#!/usr/bin/env bash
# Re-render system.svg (Python) and the supporting D2 diagrams.
#   bash docs/architecture/render.sh          # writes the .svg files
#   bash docs/architecture/render.sh --check  # CI: fail if an .svg is out of date
# Needs D2 (https://d2lang.com): brew install d2 · winget install terrastruct.d2 · or the install script.
set -euo pipefail
cd "$(dirname "$0")"
status=0
if [ "${1:-}" = "--check" ]; then
  python3 render-system.py /tmp/clipper-system-check.svg >/dev/null
  if ! cmp -s /tmp/clipper-system-check.svg system.svg; then
    echo "out of date: docs/architecture/system.svg (run: bash docs/architecture/render.sh)"
    status=1
  fi
else
  python3 render-system.py
fi
for f in *.d2; do
  svg="${f%.d2}.svg"
  if [ "${1:-}" = "--check" ]; then
    d2 "$f" "/tmp/$svg" >/dev/null 2>&1
    if ! cmp -s "/tmp/$svg" "$svg"; then
      echo "out of date: docs/architecture/$svg (run: bash docs/architecture/render.sh)"; status=1
    fi
  else
    d2 "$f" "$svg" && echo "rendered $svg"
  fi
done
exit $status
