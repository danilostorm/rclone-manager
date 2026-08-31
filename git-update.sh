#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
git pull --ff-only
if [ ! -x .git/hooks/post-merge ]; then
  if [ -f "$ROOT/scripts/deploy-current.sh" ]; then
    DEPLOY=(bash "$ROOT/scripts/deploy-current.sh")
  else
    DEPLOY=(bash "$ROOT/scripts/deploy-from-git.sh")
  fi
  if [ "$(id -u)" -eq 0 ]; then exec "${DEPLOY[@]}"; fi
  exec sudo "${DEPLOY[@]}"
fi
