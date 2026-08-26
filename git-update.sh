#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
git pull --ff-only
if [ ! -x .git/hooks/post-merge ]; then
  if [ "$(id -u)" -eq 0 ]; then exec "$ROOT/scripts/deploy-from-git.sh"; fi
  exec sudo "$ROOT/scripts/deploy-from-git.sh"
fi
