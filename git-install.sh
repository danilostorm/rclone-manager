#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
command -v git >/dev/null 2>&1 || { echo 'Git não encontrado.' >&2; exit 1; }
if [ "$(id -u)" -eq 0 ]; then
  "$ROOT/scripts/deploy-from-git.sh"
elif sudo -n true >/dev/null 2>&1; then
  sudo -n "$ROOT/scripts/deploy-from-git.sh"
else
  sudo "$ROOT/scripts/deploy-from-git.sh"
fi
HOOK="$ROOT/.git/hooks/post-merge"
cat > "$HOOK" <<HOOKEOF
#!/usr/bin/env bash
set -e
ROOT="$ROOT"
if [ "\$(id -u)" -eq 0 ]; then
  exec "\$ROOT/scripts/deploy-from-git.sh" --post-merge
fi
if sudo -n true >/dev/null 2>&1; then
  exec sudo -n "\$ROOT/scripts/deploy-from-git.sh" --post-merge
fi
echo "Git atualizado. Para aplicar o deploy: sudo \$ROOT/scripts/deploy-from-git.sh" >&2
HOOKEOF
chmod +x "$HOOK"
echo "Integração Git pronta. Próximas atualizações: cd '$ROOT' && git pull --ff-only"
