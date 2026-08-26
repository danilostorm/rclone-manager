#!/bin/bash
set -euo pipefail
VERSION="1.4.0-rc11-ha4.7.3"
APP_DIR="${APP_DIR:-/opt/rclone-manager}"
MOUNT_ROOT="${MOUNT_ROOT:-/mnt/rclone-manager-remotes}"
WEB_PORT="${WEB_PORT:-8787}"
BIND_IP="${BIND_IP:-127.0.0.1}"
SOURCE_DIR="$(cd "$(dirname "$0")" && pwd)"

[ "$(id -u)" -eq 0 ] || { echo "Execute com sudo: sudo ./install.sh"; exit 1; }
. /etc/os-release
case "${ID:-}" in zorin|ubuntu|debian) ;; *) echo "AVISO: pensado para Zorin/Ubuntu/Debian; detectado ${PRETTY_NAME:-$ID}.";; esac
export DEBIAN_FRONTEND=noninteractive
if ! command -v docker >/dev/null 2>&1; then
  apt-get update
  apt-get install -y ca-certificates curl git docker.io
  systemctl enable --now docker
fi
if ! docker compose version >/dev/null 2>&1; then
  apt-get update
  apt-get install -y docker-compose-v2 || apt-get install -y docker-compose-plugin
fi
if [ ! -e /dev/fuse ]; then apt-get update && apt-get install -y fuse3; fi
[ -e /dev/fuse ] || { echo "ERRO: /dev/fuse indisponível."; exit 1; }
mkdir -p "$APP_DIR" "$APP_DIR/data/accounts" "$APP_DIR/cache" "$APP_DIR/backups" "$MOUNT_ROOT"
chmod 700 "$APP_DIR/data" "$APP_DIR/data/accounts" || true
if [ "$SOURCE_DIR" != "$APP_DIR" ]; then
  tar --exclude='./.env' --exclude='./data' --exclude='./cache' --exclude='./backups' -C "$SOURCE_DIR" -cf - . | tar -C "$APP_DIR" -xf -
fi
chmod +x "$APP_DIR"/*.sh "$APP_DIR"/scripts/*.sh 2>/dev/null || true
MOUNT_ROOT="$MOUNT_ROOT" "$APP_DIR/scripts/prepare-mounts.sh"
if [ ! -f "$APP_DIR/.env" ]; then
  ADMIN_PASSWORD="$(openssl rand -base64 24 | tr -d '\n' | tr '/+' 'Aa' | cut -c1-24)"
  APP_SECRET="$(openssl rand -hex 32)"
  cat > "$APP_DIR/.env" <<ENV
WEB_PORT=$WEB_PORT
BIND_IP=$BIND_IP
ADMIN_USER=admin
ADMIN_PASSWORD=$ADMIN_PASSWORD
APP_SECRET=$APP_SECRET
PLATFORM_NAME=Zorin OS Desktop
PLATFORM_SUBTITLE=Zorin OS
TZ=America/Sao_Paulo
ENV
  chmod 600 "$APP_DIR/.env"
  NEW_PASSWORD="$ADMIN_PASSWORD"
else NEW_PASSWORD=""; fi
cat > /etc/systemd/system/rclone-manager-mounts.service <<UNIT
[Unit]
Description=Prepare Rclone Manager shared mount root
Before=docker.service rclone-manager.service
After=local-fs.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/bash -lc 'mkdir -p "$MOUNT_ROOT"; mountpoint -q "$MOUNT_ROOT" || mount --bind "$MOUNT_ROOT" "$MOUNT_ROOT"; mount --make-rshared "$MOUNT_ROOT"'
ExecStop=/bin/true
[Install]
WantedBy=multi-user.target
UNIT
cat > /etc/systemd/system/rclone-manager.service <<UNIT
[Unit]
Description=Rclone Manager Zorin OS
Requires=docker.service rclone-manager-mounts.service
After=docker.service network-online.target rclone-manager-mounts.service
Wants=network-online.target
[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose up -d --build
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable rclone-manager-mounts.service rclone-manager.service >/dev/null
cd "$APP_DIR" && docker compose config >/dev/null && docker compose build --pull && systemctl restart rclone-manager.service
for _ in $(seq 1 45); do docker inspect --format='{{.State.Health.Status}}' rclone-manager-vps 2>/dev/null | grep -q healthy && break; sleep 2; done
mkdir -p /usr/local/share/applications
cat > /usr/local/share/applications/rclone-manager.desktop <<DESKTOP
[Desktop Entry]
Type=Application
Name=Rclone Manager
Comment=Gerenciador Rclone, Media Pools e MultiServer HA
Exec=xdg-open http://127.0.0.1:$WEB_PORT
Icon=drive-harddisk
Terminal=false
Categories=Network;Utility;
DESKTOP
chmod 644 /usr/local/share/applications/rclone-manager.desktop
printf '\nRclone Manager Zorin OS %s instalado.\nURL: http://127.0.0.1:%s\n' "$VERSION" "$WEB_PORT"
[ -z "$NEW_PASSWORD" ] || echo "Usuário: admin | Senha inicial: $NEW_PASSWORD"
