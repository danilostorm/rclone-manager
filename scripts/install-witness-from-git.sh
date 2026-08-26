#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[ "$(id -u)" -eq 0 ] || exec sudo "$0" "$@"
TMP="$(mktemp -d /tmp/rclone-manager-witness-git.XXXXXX)"; trap 'rm -rf "$TMP"' EXIT
NAME="rclone-manager-current-base.tar.gz"
ARCHIVE="$ROOT/dist/$NAME"
if [ -f "$ARCHIVE" ]; then
  cp "$ARCHIVE" "$TMP/base.tgz"
elif [ -f "$ARCHIVE.b64" ]; then
  base64 -d "$ARCHIVE.b64" > "$TMP/base.tgz"
elif compgen -G "$ARCHIVE.b64.part-*" >/dev/null; then
  cat "$ARCHIVE.b64".part-* | base64 -d > "$TMP/base.tgz"
else
  echo "Payload Git não encontrado."; exit 1
fi
tar -xzf "$TMP/base.tgz" -C "$TMP"
exec bash "$TMP/witness/install-witness.sh" "$@"
