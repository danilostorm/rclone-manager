#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ "$(id -u)" -eq 0 ] || exec sudo "$0" "$@"
TMP="$(mktemp -d /tmp/rm-witness.XXXXXX)"; trap 'rm -rf "$TMP"' EXIT
cat "$ROOT"/payload/current-source.tar.xz.b64.part-* | base64 -d > "$TMP/payload.tar.xz"
EXP="$(awk '{print $1}' "$ROOT/payload/current-source.tar.xz.sha256")"
[ "$(sha256sum "$TMP/payload.tar.xz"|awk '{print $1}')" = "$EXP" ] || { echo 'Payload inválido.' >&2; exit 1; }
mkdir "$TMP/src"; tar -xJf "$TMP/payload.tar.xz" -C "$TMP/src"
exec bash "$TMP/src/witness/install-witness.sh" "$@"
