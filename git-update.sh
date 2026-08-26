#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
git pull --ff-only
# The post-merge hook installed by git-install.sh normally deploys. Running the
# deploy again is harmless but wasteful, so only do it when the hook is absent.
if [ ! -x .git/hooks/post-merge ]; then
  "$ROOT/scripts/deploy-from-git.sh"
fi
