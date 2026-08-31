#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLATFORM="$($ROOT/scripts/detect-platform.sh)"

case "$PLATFORM" in
  unraid) DEST=/mnt/user/appdata/rclone-manager ;;
  *) DEST=/opt/rclone-manager ;;
esac

# Existing HA hosts use the installed tree as the source-base for Git deploys.
# Apply overlays to that live source before deploy-from-git copies it into the
# temporary build tree. The running container is untouched until the normal
# validated deploy/recreate phase begins.
if [ -f "$DEST/app/app.py" ]; then
  if [ -f "$ROOT/scripts/patch-buzzheavier-fallback.py" ]; then
    python3 "$ROOT/scripts/patch-buzzheavier-fallback.py" "$DEST"
  fi
  if [ -f "$ROOT/scripts/patch-duplicate-history.py" ]; then
    python3 "$ROOT/scripts/patch-duplicate-history.py" "$DEST"
  fi
fi

exec "$ROOT/scripts/deploy-from-git.sh" "$@"
