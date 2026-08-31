#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
command -v git >/dev/null 2>&1 || { echo 'Git não encontrado.' >&2; exit 1; }
DEPLOY="$ROOT/scripts/deploy-current.sh"
[ -x "$DEPLOY" ] || DEPLOY="$ROOT/scripts/deploy-from-git.sh"
if [ "$(id -u)" -eq 0 ]; then
  "$DEPLOY"
elif sudo -n true >/dev/null 2>&1; then
  sudo -n "$DEPLOY"
else
  sudo "$DEPLOY"
fi
HOOK="$ROOT/.git/hooks/post-merge"
cat > "$HOOK" <<HOOKEOF
#!/usr/bin/env bash
set -e
ROOT="$ROOT"
DEPLOY="\$ROOT/scripts/deploy-current.sh"
[ -x "\$DEPLOY" ] || DEPLOY="\$ROOT/scripts/deploy-from-git.sh"
if [ "\$(id -u)" -eq 0 ]; then
  exec "\$DEPLOY" --post-merge
fi
if sudo -n true >/dev/null 2>&1; then
  exec sudo -n "\$DEPLOY" --post-merge
fi
echo "Git atualizado. Para aplicar o deploy: sudo \$DEPLOY" >&2
HOOKEOF
chmod +x "$HOOK"
echo "Integração Git pronta. Próximas atualizações: cd '$ROOT' && git pull --ff-only"
