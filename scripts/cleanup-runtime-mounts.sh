#!/usr/bin/env bash
set -u

MOUNT_ROOT="/mnt/rclone-manager-remotes"
MEDIA_ROOT="/media-union"

echo "Limpando mounts runtime antigos do Rclone Manager..."

# Os mounts dos Drives/Media Pools são processos rclone que podem sobreviver
# ao recreate do container e deixar FUSE em ENOTCONN. Mate apenas mounts cujo
# destino pertence ao root gerenciado pelo Rclone Manager.
pkill -f 'rclone mount .* /mnt/rclone-manager-remotes/' 2>/dev/null || true
sleep 2

lazy_unmount() {
  local target="$1"
  [ -n "$target" ] || return 0

  fusermount3 -uz "$target" 2>/dev/null || \
  fusermount -uz "$target" 2>/dev/null || \
  umount -l "$target" 2>/dev/null || true
}

# Desmonte primeiro os mounts mais profundos. O root /mnt/rclone-manager-remotes
# é um bind rshared usado pelo Docker e NÃO deve ser desmontado.
if command -v findmnt >/dev/null 2>&1; then
  while IFS= read -r target; do
    [ "$target" = "$MOUNT_ROOT" ] && continue
    lazy_unmount "$target"
  done < <(
    findmnt -rn -R "$MOUNT_ROOT" -o TARGET,FSTYPE 2>/dev/null |
      awk -v root="$MOUNT_ROOT" '$1 != root && $2 ~ /^fuse/ {print $1}' |
      awk '{print length($0), $0}' |
      sort -rn |
      cut -d' ' -f2-
  )

  # O stable path pode ser um bind para um Media Pool que acabou de ser
  # desmontado. Removê-lo aqui evita um /media-union aparentemente montado,
  # porém vazio ou preso ao mount antigo. O Agent o recria/reconcilia depois.
  while IFS= read -r target; do
    [ "$target" = "$MEDIA_ROOT" ] && continue
    lazy_unmount "$target"
  done < <(
    findmnt -rn -R "$MEDIA_ROOT" -o TARGET 2>/dev/null |
      awk -v root="$MEDIA_ROOT" '$1 != root {print $1}' |
      awk '{print length($0), $0}' |
      sort -rn |
      cut -d' ' -f2-
  )
fi

mkdir -p "$MOUNT_ROOT" "$MEDIA_ROOT"

echo "Runtime FUSE antigo limpo. Drives/Media Pools serão remontados pelo Manager; Gateways pelo Agent."
