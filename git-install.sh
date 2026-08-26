#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
command -v git >/dev/null 2>&1 || { echo 'Git não encontrado.'; exit 1; }

# Install/upgrade now, then make future plain `git pull` deploy automatically.
"$ROOT/scripts/deploy-from-git.sh"
HOOK="$ROOT/.git/hooks/post-merge"
mkdir -p "$(dirname "$HOOK")"
cat > "$HOOK" <<EOF
#!/usr/bin/env bash
set -e
ROOT="$ROOT"
if [ "\$(id -u)" -eq 0 ]; then
  exec "\$ROOT/scripts/deploy-from-git.sh" --post-merge
fi
if sudo -n true >/dev/null 2>&1; then
  exec sudo -n "\$ROOT/scripts/deploy-from-git.sh" --post-merge
fi
printf '%s\n' 'Rclone Manager atualizado no Git, mas o deploy precisa de root.' >&2
printf '%s\n' "Execute: sudo \$ROOT/scripts/deploy-from-git.sh" >&2
EOF
chmod +x "$HOOK"
echo
echo "Integração Git instalada. A partir de agora, neste checkout, 'git pull' também aplica a nova versão quando houver merge/fast-forward com post-merge."
