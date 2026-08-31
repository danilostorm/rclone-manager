#!/usr/bin/env bash
set -u

PLATFORM="${1:-}"
case "$PLATFORM" in
  unraid)
    ENV_FILE=/boot/config/plugins/rclone-manager-multiserver-agent/agent.env
    DEFAULT_STATE=/boot/config/plugins/rclone-manager-multiserver-agent/state
    ;;
  *)
    ENV_FILE=/opt/rclone-manager-multiserver-agent/agent.env
    DEFAULT_STATE=/var/lib/rclone-manager-multiserver
    ;;
esac

[ -f "$ENV_FILE" ] || exit 0

read_env() {
  local key="$1"
  sed -n "s/^${key}=//p" "$ENV_FILE" | tail -1 | tr -d '\r\n'
}

TOKEN="$(read_env MS_AGENT_TOKEN)"
BIND="$(read_env MS_BIND)"
PORT="$(read_env MS_PORT)"
STATE_DIR="$(read_env MS_STATE_DIR)"

[ -n "$TOKEN" ] || exit 0
[ -n "$BIND" ] || BIND=127.0.0.1
[ -n "$PORT" ] || PORT=8765
[ -n "$STATE_DIR" ] || STATE_DIR="$DEFAULT_STATE"
STATE_FILE="$STATE_DIR/state.json"
[ -f "$STATE_FILE" ] || exit 0
command -v curl >/dev/null 2>&1 || exit 0

# Aguarde o Agent responder antes de restaurar os stable paths.
for _ in $(seq 1 30); do
  if curl -fsS --connect-timeout 2 \
      -H "Authorization: Bearer $TOKEN" \
      "http://${BIND}:${PORT}/v1/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "Reconciliando bibliotecas persistidas no MultiServer Agent..."

python3 - "$STATE_FILE" <<'PY' |
import json, sys
p=sys.argv[1]
try:
    d=json.load(open(p, encoding='utf-8'))
except Exception:
    raise SystemExit(0)
for slug,lib in (d.get('libraries') or {}).items():
    if not isinstance(lib, dict):
        continue
    bid=str(lib.get('backend_id') or '').strip()
    stable=str(lib.get('stable_path') or '').strip()
    if slug and bid and stable:
        print(f"{slug}\t{bid}\t{stable}")
PY
while IFS=$'\t' read -r slug backend stable; do
  [ -n "$slug" ] || continue
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
      echo "Gateway $slug reconciliado: $backend -> $stable"
      ok=1
      break
    fi
    sleep 2
  done
  [ "$ok" -eq 1 ] || echo "AVISO: Gateway $slug ainda não pôde ser reconciliado; o monitor HA tentará novamente."
done
