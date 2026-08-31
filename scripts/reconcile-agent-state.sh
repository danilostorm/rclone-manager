#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '\r\n' < "$ROOT/VERSION" 2>/dev/null || true)"
PLATFORM="${1:-}"
SERVICE="rclone-manager-multiserver-agent.service"

case "$PLATFORM" in
  unraid)
    ENV_FILE=/boot/config/plugins/rclone-manager-multiserver-agent/agent.env
    DEFAULT_STATE=/boot/config/plugins/rclone-manager-multiserver-agent/state
    DEST=/mnt/user/appdata/rclone-manager
    LIVE_AGENT=/boot/config/plugins/rclone-manager-multiserver-agent/agent.py
    ;;
  *)
    ENV_FILE=""
    DEFAULT_STATE=/var/lib/rclone-manager-multiserver
    DEST=/opt/rclone-manager
    LIVE_AGENT=/opt/rclone-manager-multiserver-agent/agent.py
    ;;
esac

# Em VPS/Ubuntu o instalador histórico nem sempre guardou agent.env em /opt.
# Antes de reconciliar, sincronize o Agent empacotado pelo deploy e descubra
# o EnvironmentFile real do serviço systemd (ou leia o ambiente do processo).
if [ "$PLATFORM" != "unraid" ] && command -v systemctl >/dev/null 2>&1; then
  if systemctl cat "$SERVICE" >/dev/null 2>&1; then
    if [ -f "$DEST/agent/agent.py" ]; then
      if [ ! -f "$LIVE_AGENT" ] || ! cmp -s "$DEST/agent/agent.py" "$LIVE_AGENT"; then
        echo "Atualizando MultiServer Agent para ${VERSION:-versão do deploy}..."
        install -D -m 755 "$DEST/agent/agent.py" "$LIVE_AGENT"
        systemctl restart "$SERVICE" || true
        sleep 2
      fi
    fi

    detected_env="$(systemctl cat "$SERVICE" 2>/dev/null |
      sed -nE 's/^[[:space:]]*EnvironmentFile=[-]?"?([^"[:space:]]+)"?.*/\1/p' |
      tail -1)"
    if [ -n "$detected_env" ] && [ -f "$detected_env" ]; then
      ENV_FILE="$detected_env"
    else
      for candidate in \
        /opt/rclone-manager-multiserver-agent/agent.env \
        /etc/default/rclone-manager-multiserver-agent \
        /etc/rclone-manager-multiserver-agent.env; do
        if [ -f "$candidate" ]; then
          ENV_FILE="$candidate"
          break
        fi
      done
    fi
  fi
fi

read_env_file() {
  local key="$1"
  [ -n "${ENV_FILE:-}" ] && [ -f "$ENV_FILE" ] || return 0
  sed -n "s/^${key}=//p" "$ENV_FILE" | tail -1 | tr -d '\r\n'
}

read_proc_env() {
  local key="$1" pid=""
  [ "$PLATFORM" != "unraid" ] || return 0
  command -v systemctl >/dev/null 2>&1 || return 0
  pid="$(systemctl show -p MainPID --value "$SERVICE" 2>/dev/null || true)"
  [ -n "$pid" ] && [ "$pid" != "0" ] && [ -r "/proc/$pid/environ" ] || return 0
  tr '\0' '\n' < "/proc/$pid/environ" |
    sed -n "s/^${key}=//p" | tail -1 | tr -d '\r\n'
}

get_env() {
  local key="$1" value=""
  value="$(read_env_file "$key")"
  [ -n "$value" ] || value="$(read_proc_env "$key")"
  printf '%s' "$value"
}

TOKEN="$(get_env MS_AGENT_TOKEN)"
BIND="$(get_env MS_BIND)"
PORT="$(get_env MS_PORT)"
STATE_DIR="$(get_env MS_STATE_DIR)"

if [ -z "$TOKEN" ]; then
  echo "AVISO: token do MultiServer Agent não pôde ser descoberto; Gateway será reconciliado pelo monitor HA." >&2
  exit 0
fi
[ -n "$BIND" ] || BIND=127.0.0.1
[ -n "$PORT" ] || PORT=8765
[ -n "$STATE_DIR" ] || STATE_DIR="$DEFAULT_STATE"
STATE_FILE="$STATE_DIR/state.json"
[ -f "$STATE_FILE" ] || exit 0
command -v curl >/dev/null 2>&1 || exit 0

agent_ready=0
for _ in $(seq 1 30); do
  if curl -fsS --connect-timeout 2 \
      -H "Authorization: Bearer $TOKEN" \
      "http://${BIND}:${PORT}/v1/health" >/dev/null 2>&1; then
    agent_ready=1
    break
  fi
  sleep 1
done
[ "$agent_ready" -eq 1 ] || {
  echo "AVISO: MultiServer Agent não respondeu em ${BIND}:${PORT}; monitor HA tentará novamente." >&2
  exit 0
}

echo "Reconciliando bibliotecas persistidas no MultiServer Agent..."

python3 - "$STATE_FILE" <<'PY' |
import json, sys
p=sys.argv[1]
try:
    d=json.load(open(p, encoding='utf-8'))
except Exception:
    raise SystemExit(0)
backends=d.get('backends') or {}
for slug,lib in (d.get('libraries') or {}).items():
    if not isinstance(lib, dict):
        continue
    bid=str(lib.get('backend_id') or '').strip()
    stable=str(lib.get('stable_path') or '').strip()
    backend=backends.get(bid) if isinstance(backends, dict) else None
    backend=backend if isinstance(backend, dict) else {}
    transport=str(backend.get('transport') or '').strip()
    source=str(backend.get('source_path') or '').strip()
    if slug and bid and stable:
        print(f"{slug}\t{bid}\t{stable}\t{transport}\t{source}")
PY
while IFS=$'\t' read -r slug backend stable transport source; do
  [ -n "$slug" ] || continue

  # Um backend local só pode ser ativado quando a origem real já estiver
  # montada. Isso impede bind de diretório vazio e falso mounted/readable=true
  # enquanto Drives/Media Pool ainda estão remontando após update/recreate.
  if [ "$transport" = "local" ] && [ -n "$source" ]; then
    source_ready=0
    echo "Aguardando origem local de $slug ficar pronta: $source"
    for _ in $(seq 1 60); do
      if mountpoint -q "$source" 2>/dev/null; then
        if timeout 5 stat "$source" >/dev/null 2>&1; then
          source_ready=1
          break
        fi
      fi
      sleep 2
    done
    if [ "$source_ready" -ne 1 ]; then
      echo "AVISO: origem local de $slug não virou mountpoint em tempo hábil ($source); stable path NÃO será apontado para diretório vazio." >&2
      continue
    fi
  fi

  ok=0
  for _ in $(seq 1 30); do
    payload="$(python3 - "$slug" "$backend" "$stable" <<'PY'
import json,sys
print(json.dumps({"library_slug":sys.argv[1],"backend_id":sys.argv[2],"stable_path":sys.argv[3]}))
PY
)"
    response="$(curl -sS --connect-timeout 3 --max-time 12 \
      -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H 'Content-Type: application/json' \
      --data "$payload" \
      "http://${BIND}:${PORT}/v1/gateway/switch" 2>/dev/null || true)"
    if python3 - "$response" <<'PY' >/dev/null 2>&1
import json,sys
try:
    d=json.loads(sys.argv[1])
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if d.get('ok') else 1)
PY
    then
      # Não aceite sucesso HTTP sozinho: confirme que o stable path virou
      # mountpoint e responde a stat antes de declarar a reconciliação pronta.
      if mountpoint -q "$stable" 2>/dev/null && timeout 5 stat "$stable" >/dev/null 2>&1; then
        echo "Gateway $slug reconciliado: $backend -> $stable"
        ok=1
        break
      fi
    fi
    sleep 2
  done
  [ "$ok" -eq 1 ] || echo "AVISO: Gateway $slug ainda não pôde ser reconciliado; o monitor HA tentará novamente."
done
