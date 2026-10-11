#!/usr/bin/env bash
# Install the independent HA Media Gateway watchdog without rebuilding or
# restarting Rclone Manager, Plex or Jellyfin.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MAIN="$ROOT/scripts/media-gateway-watchdog.py"
PLATFORM="$("$ROOT/scripts/detect-platform.sh")"
MODE="--check"
[ "$#" -eq 0 ] || MODE="$1"

[ "$(id -u)" -eq 0 ] || { echo "Execute como root." >&2; exit 1; }
[ "$MODE" = "--check" ] || [ "$MODE" = "--install" ] || {
  echo "Uso: bash scripts/install-media-gateway-watchdog.sh [--check|--install]" >&2
  exit 2
}

command -v python3 >/dev/null || { echo "Python 3 não encontrado." >&2; exit 1; }
python3 -m py_compile "$MAIN"
python3 "$ROOT/scripts/test-media-gateway-watchdog.py"

echo "===== WATCHDOG / $PLATFORM ====="
python3 "$MAIN" --platform "$PLATFORM" --once

if [ "$MODE" = "--check" ]; then
  echo
  echo "Diagnóstico concluído; nada foi instalado nem remontado."
  echo "Para ativar: bash '$ROOT/scripts/install-media-gateway-watchdog.sh' --install"
  exit 0
fi

if [ "$PLATFORM" = unraid ]; then
  BOOT_DIR="/boot/config/plugins/rclone-manager-media-watchdog"
  STARTER="$BOOT_DIR/start.sh"
  GO="/boot/config/go"

  mkdir -p "$BOOT_DIR"
  cat > "$STARTER" <<'SH'
#!/usr/bin/env bash
# Wait for the Unraid array/user share: /boot/config/go runs before some shares
# become accessible. flock in the Python process prevents duplicate loops.
ROOT="/mnt/user/appdata/rclone-manager-src"
MAIN="$ROOT/scripts/media-gateway-watchdog.py"
for _ in $(seq 1 180); do
  [ -f "$MAIN" ] && [ -d /mnt/user/appdata/rclone-manager/data ] && break
  sleep 20
done
[ -f "$MAIN" ] || exit 0
STATE="/mnt/user/appdata/rclone-manager/data/media-gateway-watchdog"
mkdir -p "$STATE"
exec /usr/bin/python3 "$MAIN" --platform unraid --loop --repair --interval 90 \
  >> "$STATE/watchdog.log" 2>&1
SH
  chmod 700 "$STARTER"

  if [ ! -f "$GO" ]; then
    echo "#!/bin/bash" > "$GO"
    chmod 755 "$GO"
  fi
  if ! grep -Fq '# RM_MEDIA_GATEWAY_WATCHDOG_V1' "$GO"; then
    cp -p "$GO" "$GO.rm-media-backup-$(date +%Y%m%d%H%M%S)"
    cat >> "$GO" <<'GOHOOK'

# RM_MEDIA_GATEWAY_WATCHDOG_V1
/bin/bash /boot/config/plugins/rclone-manager-media-watchdog/start.sh &
GOHOOK
  fi

  # Only our new background watcher is started. None of the media services
  # or existing FUSE mounts is restarted or unmounted at installation.
  bash "$STARTER" </dev/null >/dev/null 2>&1 &
  echo "Watchdog instalado no Unraid. Inicialização persistida em $GO."
  echo "Log: /mnt/user/appdata/rclone-manager/data/media-gateway-watchdog/watchdog.log"

else
  command -v systemctl >/dev/null || {
    echo "systemd não disponível. Execute manualmente: python3 '$MAIN' --platform '$PLATFORM' --loop --repair" >&2
    exit 1
  }
  UNIT="/etc/systemd/system/rclone-manager-media-watchdog.service"
  cat > "$UNIT" <<SERVICE
[Unit]
Description=Rclone Manager Media Gateway Watchdog ($PLATFORM)
Wants=network-online.target
After=network-online.target docker.service

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 $MAIN --platform $PLATFORM --loop --repair --interval 90
Restart=always
RestartSec=15
NoNewPrivileges=true

[Install]
WantedBy=multi-user.target
SERVICE
  systemctl daemon-reload
  systemctl enable --now rclone-manager-media-watchdog.service
  echo "Watchdog instalado no systemd ($PLATFORM)."
  echo "Estado: systemctl status rclone-manager-media-watchdog --no-pager"
  echo "Logs: journalctl -u rclone-manager-media-watchdog -n 60 --no-pager"
fi

echo "A recuperação só ocorre após 2 verificações ruins; cooldown 10 minutos."
