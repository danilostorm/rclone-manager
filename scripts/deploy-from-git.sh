#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '\r\n' < "$ROOT/VERSION")"
PLATFORM="$($ROOT/scripts/detect-platform.sh)"
[ "$(id -u)" -eq 0 ] || { echo "Deploy exige root. Use sudo $ROOT/scripts/deploy-from-git.sh" >&2; exit 1; }
command -v docker >/dev/null 2>&1 || { echo 'Docker não encontrado.' >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo 'Docker Compose v2 não encontrado.' >&2; exit 1; }
[ -e /dev/fuse ] || { echo '/dev/fuse não encontrado.' >&2; exit 1; }

case "$PLATFORM" in
  unraid)
    DEST=/mnt/user/appdata/rclone-manager
    CONTAINER=rclone-manager
    PLATFORM_NAME='Unraid / AEROCOOL'
    PLATFORM_SUBTITLE='Unraid'
    ;;
  zorin)
    DEST=/opt/rclone-manager
    CONTAINER=rclone-manager-zorin
    PLATFORM_NAME='Zorin OS'
    PLATFORM_SUBTITLE='Zorin OS / Desktop Linux'
    ;;
  *)
    DEST=/opt/rclone-manager
    CONTAINER=rclone-manager-vps
    PLATFORM_NAME='Linux / VPS'
    PLATFORM_SUBTITLE='Ubuntu / Debian / Oracle'
    ;;
esac

TMP="$(mktemp -d /tmp/rclone-manager-git.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
cat "$ROOT"/payload/current-source.tar.xz.b64.part-* | base64 -d > "$TMP/current-source.tar.xz"
EXPECTED="$(awk '{print $1}' "$ROOT/payload/current-source.tar.xz.sha256")"
ACTUAL="$(sha256sum "$TMP/current-source.tar.xz" | awk '{print $1}')"
if [ "$EXPECTED" != "$ACTUAL" ]; then
  if git -C "$ROOT" diff --quiet -- payload/current-source.tar.xz.b64.part-* payload/current-source.tar.xz.sha256; then
    echo "AVISO: manifesto SHA256 do payload está desatualizado (esperado $EXPECTED, obtido $ACTUAL), mas os arquivos estão íntegros no commit Git atual; continuando." >&2
  else
    echo "SHA256 inválido e payload possui alterações locais: esperado $EXPECTED, obtido $ACTUAL" >&2
    exit 1
  fi
fi
mkdir -p "$TMP/source"
tar -xJf "$TMP/current-source.tar.xz" -C "$TMP/source"
[ -f "$TMP/source/app/app.py" ] || { echo 'Payload inválido: app/app.py ausente.' >&2; exit 1; }
python3 "$ROOT/scripts/patch-git-source.py" "$TMP/source" "$VERSION"

mkdir -p "$DEST" "$DEST/data/accounts" "$DEST/cache" "$DEST/backups" /mnt/rclone-manager-remotes /media-union
chmod 700 "$DEST/data" "$DEST/data/accounts" 2>/dev/null || true
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP="$DEST/backups/git-pre-${VERSION}-${TS}"
mkdir -p "$BACKUP"
if [ -d "$DEST/app" ]; then
  tar -czf "$BACKUP/code.tar.gz" \
    --exclude='./data' --exclude='./cache' --exclude='./backups' --exclude='./.env' \
    -C "$DEST" . 2>/dev/null || true
fi

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

find "$DEST" -mindepth 1 -maxdepth 1 \
  ! -name data ! -name cache ! -name backups ! -name .env \
  -exec rm -rf -- {} +
tar -C "$TMP/source" -cf - . | tar -C "$DEST" -xf -

mkdir -p "$DEST/cache"
find "$DEST/cache" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +

if [ ! -f "$DEST/.env" ]; then
  ADMIN_PASSWORD="$(openssl rand -base64 24 2>/dev/null | tr -d '\n' | tr '/+' 'Aa' | cut -c1-24 || true)"
  [ -n "$ADMIN_PASSWORD" ] || ADMIN_PASSWORD="rm-$(date +%s)-$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')"
  APP_SECRET="$(openssl rand -hex 32 2>/dev/null || od -An -N32 -tx1 /dev/urandom | tr -d ' \n')"
  cat > "$DEST/.env" <<ENV
WEB_PORT=8787
BIND_IP=0.0.0.0
ADMIN_USER=admin
ADMIN_PASSWORD=$ADMIN_PASSWORD
APP_SECRET=$APP_SECRET
TZ=America/Sao_Paulo
ENV
  chmod 600 "$DEST/.env"
  echo "Senha inicial admin: $ADMIN_PASSWORD"
fi

set_env(){
  local k="$1" v="$2"
  if grep -qE "^${k}=" "$DEST/.env"; then
    sed -i "s|^${k}=.*|${k}=${v}|" "$DEST/.env"
  else
    printf '%s=%s\n' "$k" "$v" >> "$DEST/.env"
  fi
}
set_env APP_VERSION "$VERSION"
set_env CONTAINER_NAME "$CONTAINER"
set_env PLATFORM_NAME "$PLATFORM_NAME"
set_env PLATFORM_SUBTITLE "$PLATFORM_SUBTITLE"

mkdir -p /mnt/rclone-manager-remotes
if ! mountpoint -q /mnt/rclone-manager-remotes; then
  mount --bind /mnt/rclone-manager-remotes /mnt/rclone-manager-remotes
fi
mount --make-rshared /mnt/rclone-manager-remotes || true

cd "$DEST"
docker compose --env-file .env config >/dev/null
docker compose --env-file .env build --pull
docker compose --env-file .env up -d --force-recreate

for _ in $(seq 1 60); do
  STATUS="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CONTAINER" 2>/dev/null || true)"
  [ "$STATUS" = healthy ] && break
  sleep 2
done
STATUS="$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$CONTAINER" 2>/dev/null || true)"
[ "$STATUS" = healthy ] || { echo "Container $CONTAINER não ficou healthy (status=$STATUS)." >&2; docker logs --tail 150 "$CONTAINER" 2>&1 || true; exit 1; }

if [ "$PLATFORM" = unraid ] && [ -f /boot/config/plugins/rclone-manager-multiserver-agent/agent.py ]; then
  cp -f "$DEST/agent/agent.py" /boot/config/plugins/rclone-manager-multiserver-agent/agent.py
  pkill -f '/boot/config/plugins/rclone-manager-multiserver-agent/agent.py' 2>/dev/null || true
  sleep 1
  [ ! -f /boot/config/plugins/rclone-manager-multiserver-agent/start.sh ] || bash /boot/config/plugins/rclone-manager-multiserver-agent/start.sh || true
elif systemctl list-unit-files 2>/dev/null | grep -q '^rclone-manager-multiserver-agent.service'; then
  install -D -m 755 "$DEST/agent/agent.py" /opt/rclone-manager-multiserver-agent/agent.py
  systemctl restart rclone-manager-multiserver-agent
fi

if systemctl list-unit-files 2>/dev/null | grep -q '^rclone-manager-witness.service'; then
  install -D -m 755 "$DEST/witness/witness.py" /opt/rclone-manager-witness/witness.py
  systemctl restart rclone-manager-witness
fi

[ ! -x /usr/local/sbin/rclone-manager-agent-firewall.sh ] || /usr/local/sbin/rclone-manager-agent-firewall.sh || true

echo
echo "Rclone Manager $VERSION aplicado via Git."
echo "Plataforma: $PLATFORM"
echo "Destino: $DEST"
echo "Container: $CONTAINER ($STATUS)"
echo "Backup anterior: $BACKUP"
