#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
git pull --ff-only
if [ ! -x .git/hooks/post-merge ]; then
  DEPLOY="$ROOT/scripts/deploy-current.sh"
  [ -x "$DEPLOY" ] || DEPLOY="$ROOT/scripts/deploy-from-git.sh"
  if [ "$(id -u)" -eq 0 ]; then exec "$DEPLOY"; fi
  exec sudo "$DEPLOY"
fi
