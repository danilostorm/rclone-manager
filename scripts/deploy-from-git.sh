#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PLATFORM="${RCLONE_MANAGER_PLATFORM:-$($ROOT/scripts/detect-platform.sh)}"
case "$PLATFORM" in unraid|vps|zorin) ;; *) echo "Plataforma inválida: $PLATFORM"; exit 1 ;; esac

NAME="rclone-manager-current-base.tar.gz"
ARCHIVE="$ROOT/dist/$NAME"
ARCHIVE_B64="$ROOT/dist/$NAME.b64"

if [ "$(id -u)" -ne 0 ]; then
  if sudo -n true >/dev/null 2>&1; then exec sudo -n "$0" "$@"; fi
  echo "Execute com sudo/root: sudo $0"; exit 1
fi

TMP="$(mktemp -d /tmp/rclone-manager-git.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
if [ -f "$ARCHIVE" ]; then
  SRC_ARCHIVE="$ARCHIVE"
elif [ -f "$ARCHIVE_B64" ]; then
  SRC_ARCHIVE="$TMP/$NAME"
  base64 -d "$ARCHIVE_B64" > "$SRC_ARCHIVE"
else
  echo "Release ausente: $ARCHIVE ou $ARCHIVE_B64"; exit 1
fi

if [ -f "$ROOT/SHA256SUMS" ]; then
  EXPECTED="$(awk -v n="dist/$NAME" '$2==n {print $1}' "$ROOT/SHA256SUMS" | head -1)"
  if [ -n "$EXPECTED" ]; then
    ACTUAL="$(sha256sum "$SRC_ARCHIVE" | awk '{print $1}')"
    [ "$ACTUAL" = "$EXPECTED" ] || { echo "SHA256 inválido para $NAME"; exit 1; }
  fi
fi

tar -xzf "$SRC_ARCHIVE" -C "$TMP"
# Base payload is the current Unraid build. VPS/Zorin differ only in the
# installer and Compose definition, avoiding 3 almost-identical payloads.
if [ "$PLATFORM" != unraid ]; then
  cp "$ROOT/platform/$PLATFORM/install.sh" "$TMP/install.sh"
  cp "$ROOT/platform/$PLATFORM/docker-compose.yml" "$TMP/docker-compose.yml"
fi
chmod +x "$TMP"/*.sh "$TMP"/scripts/*.sh 2>/dev/null || true

echo "Rclone Manager Git deploy: plataforma=$PLATFORM versão=$(cat "$ROOT/VERSION")"
"$TMP/install.sh"

if [ "$PLATFORM" = unraid ]; then
  AGENT_DIR=/boot/config/plugins/rclone-manager-multiserver-agent
  if [ -f "$AGENT_DIR/agent.py" ] && [ -f "$TMP/agent/agent.py" ]; then
    cp -a "$AGENT_DIR/agent.py" "$AGENT_DIR/agent.py.pre-git-update" 2>/dev/null || true
    cp "$TMP/agent/agent.py" "$AGENT_DIR/agent.py"
    pkill -f "$AGENT_DIR/agent.py" 2>/dev/null || true
    sleep 1
    bash "$AGENT_DIR/start.sh" || true
  fi
else
  AGENT_DIR=/opt/rclone-manager-multiserver-agent
  if [ -f "$AGENT_DIR/agent.py" ] && [ -f "$TMP/agent/agent.py" ]; then
    cp -a "$AGENT_DIR/agent.py" "$AGENT_DIR/agent.py.pre-git-update" 2>/dev/null || true
    cp "$TMP/agent/agent.py" "$AGENT_DIR/agent.py"
    systemctl restart rclone-manager-multiserver-agent 2>/dev/null || true
  fi
fi

if [ -f /opt/rclone-manager-witness/witness.py ] && [ -f "$TMP/witness/witness.py" ]; then
  cp -a /opt/rclone-manager-witness/witness.py /opt/rclone-manager-witness/witness.py.pre-git-update 2>/dev/null || true
  cp "$TMP/witness/witness.py" /opt/rclone-manager-witness/witness.py
  systemctl restart rclone-manager-witness 2>/dev/null || true
fi

echo "Deploy concluído: $(cat "$ROOT/VERSION")"
