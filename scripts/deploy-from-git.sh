#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '\r\n' < "$ROOT/VERSION")"
PLATFORM="$($ROOT/scripts/detect-platform.sh)"

[ "$(id -u)" -eq 0 ] || {
  echo "Deploy exige root. Use sudo $ROOT/scripts/deploy-from-git.sh" >&2
  exit 1
}
command -v docker >/dev/null 2>&1 || { echo 'Docker não encontrado.' >&2; exit 1; }
docker compose version >/dev/null 2>&1 || { echo 'Docker Compose v2 não encontrado.' >&2; exit 1; }
[ -e /dev/fuse ] || { echo '/dev/fuse não encontrado.' >&2; exit 1; }

case "$PLATFORM" in
  unraid)
    DEST=/mnt/user/appdata/rclone-manager
    CONTAINER=rclone-manager
    PLATFORM_NAME='Unraid / AEROCOOL'
    PLATFORM_SUBTITLE='Unraid'
    AGENT_LIVE=/boot/config/plugins/rclone-manager-multiserver-agent/agent.py
    ;;
  zorin)
    DEST=/opt/rclone-manager
    CONTAINER=rclone-manager-zorin
    PLATFORM_NAME='Zorin OS'
    PLATFORM_SUBTITLE='Zorin OS / Desktop Linux'
    AGENT_LIVE=/opt/rclone-manager-multiserver-agent/agent.py
    ;;
  *)
    DEST=/opt/rclone-manager
    CONTAINER=rclone-manager-vps
    PLATFORM_NAME='Linux / VPS'
    PLATFORM_SUBTITLE='Ubuntu / Debian / Oracle'
    AGENT_LIVE=/opt/rclone-manager-multiserver-agent/agent.py
    ;;
esac

TMP="$(mktemp -d /tmp/rclone-manager-git.XXXXXX)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/source"

# Migração segura: em hosts que já executam HA4.x, o código instalado é a
# fonte-base. Isso evita depender de um bundle antigo e preserva exatamente as
# correções já aplicadas naquele host. O Git aplica somente o overlay atual.
if [ -f "$DEST/app/app.py" ] && grep -Eq '1\.4\.0-rc11-ha4' "$DEST/app/app.py"; then
  echo "Instalação HA existente detectada em $DEST; usando-a como base da migração Git."
  tar -C "$DEST" \
    --exclude='./data' --exclude='./cache' --exclude='./backups' --exclude='./.env' \
    -cf - . | tar -C "$TMP/source" -xf -
  SOURCE_MODE=live

  if [ ! -f "$TMP/source/agent/agent.py" ] && [ -f "$AGENT_LIVE" ]; then
    mkdir -p "$TMP/source/agent"
    cp -a "$AGENT_LIVE" "$TMP/source/agent/agent.py"
  fi
  if [ ! -f "$TMP/source/witness/witness.py" ] && [ -f /opt/rclone-manager-witness/witness.py ]; then
    mkdir -p "$TMP/source/witness"
    cp -a /opt/rclone-manager-witness/witness.py "$TMP/source/witness/witness.py"
    [ ! -f /opt/rclone-manager-witness/install-witness.sh ] || \
      cp -a /opt/rclone-manager-witness/install-witness.sh "$TMP/source/witness/install-witness.sh"
  fi
else
  SOURCE_MODE=payload
  PARTS=("$ROOT"/payload/current-source.tar.xz.b64.part-*)
  [ -e "${PARTS[0]}" ] || {
    echo 'Instalação nova exige payload completo, mas nenhuma parte foi encontrada.' >&2
    exit 1
  }
  cat "${PARTS[@]}" | base64 -d > "$TMP/current-source.tar.xz" || {
    echo 'Payload base64 corrompido/incompleto.' >&2
    exit 1
  }
  EXPECTED="$(awk '{print $1}' "$ROOT/payload/current-source.tar.xz.sha256")"
  ACTUAL="$(sha256sum "$TMP/current-source.tar.xz" | awk '{print $1}')"
  [ -n "$EXPECTED" ] && [ "$EXPECTED" = "$ACTUAL" ] || {
    echo "SHA256 inválido: esperado $EXPECTED, obtido $ACTUAL" >&2
    exit 1
  }
  xz -t "$TMP/current-source.tar.xz" || {
    echo 'Payload XZ corrompido ou incompleto.' >&2
    exit 1
  }
  tar -xJf "$TMP/current-source.tar.xz" -C "$TMP/source"
fi

[ -f "$TMP/source/app/app.py" ] || { echo 'Fonte inválida: app/app.py ausente.' >&2; exit 1; }
[ -f "$TMP/source/app/drive_links.py" ] || { echo 'Fonte inválida: app/drive_links.py ausente.' >&2; exit 1; }
[ -f "$TMP/source/docker-compose.yml" ] || { echo 'Fonte inválida: docker-compose.yml ausente.' >&2; exit 1; }
[ -f "$TMP/source/Dockerfile" ] || { echo 'Fonte inválida: Dockerfile ausente.' >&2; exit 1; }
[ -f "$TMP/source/requirements.txt" ] || { echo 'Fonte inválida: requirements.txt ausente.' >&2; exit 1; }

python3 "$ROOT/scripts/patch-git-source.py" "$TMP/source" "$VERSION"
printf '%s\n' "$VERSION" > "$TMP/source/VERSION"

# O bootstrap MultiServer usa Paramiko nas versões HA4 atuais.
grep -qE '^paramiko([<=>]|$)' "$TMP/source/requirements.txt" || \
  printf '%s\n' 'paramiko>=3.4,<4' >> "$TMP/source/requirements.txt"

# Ajusta identificadores de versão dos componentes auxiliares sem alterar
# comportamento/protocolo. Arquivos ausentes são permitidos em instalações que
# não usam aquele componente localmente.
python3 - "$TMP/source" "$VERSION" <<'PY'
from pathlib import Path
import re, sys
root=Path(sys.argv[1]); version=sys.argv[2]
for rel in [
    'agent/agent.py',
    'app/bootstrap_assets/agent.py',
]:
    p=root/rel
    if p.exists():
        s=p.read_text(encoding='utf-8', errors='replace')
        s=re.sub(r'(?m)^VERSION\s*=\s*["\'][^"\']+["\']', f'VERSION = "{version}"', s, count=1)
        p.write_text(s, encoding='utf-8')
PY

python3 -m py_compile \
  "$TMP/source/app/app.py" \
  "$TMP/source/app/drive_links.py"
[ ! -f "$TMP/source/app/multiserver.py" ] || python3 -m py_compile "$TMP/source/app/multiserver.py"
[ ! -f "$TMP/source/app/multiserver_bootstrap.py" ] || python3 -m py_compile "$TMP/source/app/multiserver_bootstrap.py"
[ ! -f "$TMP/source/app/mounts.py" ] || python3 -m py_compile "$TMP/source/app/mounts.py"
[ ! -f "$TMP/source/app/media_pools.py" ] || python3 -m py_compile "$TMP/source/app/media_pools.py"

# Nada de produção é parado antes de toda validação acima terminar.
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

# Mantém banco/OAuth/cache/configuração; troca apenas código/arquivos de deploy.
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
find "$DEST" -mindepth 1 -maxdepth 1 \
  ! -name data ! -name cache ! -name backups ! -name .env \
  -exec rm -rf -- {} +
tar -C "$TMP/source" -cf - . | tar -C "$DEST" -xf -

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
if [ "$STATUS" != healthy ]; then
  echo "Container $CONTAINER não ficou healthy (status=$STATUS)." >&2
  docker logs --tail 150 "$CONTAINER" 2>&1 || true
  echo "Backup disponível em: $BACKUP" >&2
  exit 1
fi

if [ "$PLATFORM" = unraid ] && [ -f /boot/config/plugins/rclone-manager-multiserver-agent/agent.py ] && [ -f "$DEST/agent/agent.py" ]; then
  cp -f "$DEST/agent/agent.py" /boot/config/plugins/rclone-manager-multiserver-agent/agent.py
  pkill -f '/boot/config/plugins/rclone-manager-multiserver-agent/agent.py' 2>/dev/null || true
  sleep 1
  [ ! -f /boot/config/plugins/rclone-manager-multiserver-agent/start.sh ] || \
    bash /boot/config/plugins/rclone-manager-multiserver-agent/start.sh || true
elif systemctl list-unit-files 2>/dev/null | grep -q '^rclone-manager-multiserver-agent.service' && [ -f "$DEST/agent/agent.py" ]; then
  install -D -m 755 "$DEST/agent/agent.py" /opt/rclone-manager-multiserver-agent/agent.py
  systemctl restart rclone-manager-multiserver-agent
fi

if systemctl list-unit-files 2>/dev/null | grep -q '^rclone-manager-witness.service' && [ -f "$DEST/witness/witness.py" ]; then
  install -D -m 755 "$DEST/witness/witness.py" /opt/rclone-manager-witness/witness.py
  systemctl restart rclone-manager-witness
fi

[ ! -x /usr/local/sbin/rclone-manager-agent-firewall.sh ] || /usr/local/sbin/rclone-manager-agent-firewall.sh || true

echo
echo "Rclone Manager $VERSION aplicado via Git."
echo "Fonte-base: $SOURCE_MODE"
echo "Plataforma: $PLATFORM"
echo "Destino: $DEST"
echo "Container: $CONTAINER ($STATUS)"
echo "Backup anterior: $BACKUP"
