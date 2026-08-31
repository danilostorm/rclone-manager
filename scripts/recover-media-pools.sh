#!/usr/bin/env bash
set -u

PLATFORM="${1:-}"
case "$PLATFORM" in
  unraid)
    DEST=/mnt/user/appdata/rclone-manager
    CONTAINER=rclone-manager
    ;;
  zorin)
    DEST=/opt/rclone-manager
    CONTAINER=rclone-manager-zorin
    ;;
  *)
    DEST=/opt/rclone-manager
    CONTAINER=rclone-manager-vps
    ;;
esac

POOL_DATA="$DEST/data/media-pools"
MOUNT_ROOT=/mnt/rclone-manager-remotes
POOL_ROOT="$MOUNT_ROOT/_media-pools"

[ -d "$POOL_DATA" ] || exit 0
command -v docker >/dev/null 2>&1 || exit 0

echo "Validando Media Pools depois da remontagem dos Drives..."

is_fuse_mount() {
  local target="$1"
  findmnt -rn -M "$target" -o FSTYPE 2>/dev/null | grep -qx 'fuse.rclone'
}

lazy_unmount() {
  local target="$1"
  fusermount3 -uz "$target" 2>/dev/null || \
  fusermount -uz "$target" 2>/dev/null || \
  umount -l "$target" 2>/dev/null || true
}

for conf in "$POOL_DATA"/*/rclone.conf; do
  [ -f "$conf" ] || continue

  slug="$(basename "$(dirname "$conf")")"
  target="$POOL_ROOT/$slug"

  if is_fuse_mount "$target"; then
    echo "Media Pool $slug já está montado."
    continue
  fi

  # Aguarda os mounts-base citados no combine config. Pegamos apenas o primeiro
  # componente abaixo de /mnt/rclone-manager-remotes para tolerar subpastas com
  # espaços nos upstreams.
  mapfile -t roots < <(
    grep -oE '/mnt/rclone-manager-remotes/[^/[:space:],]+' "$conf" 2>/dev/null |
      grep -v '/_media-pools/' |
      sort -u
  )

  if [ "${#roots[@]}" -gt 0 ]; then
    echo "Aguardando Drives-base de $slug ficarem prontos..."
    for _ in $(seq 1 60); do
      ready=1
      for root in "${roots[@]}"; do
        if ! findmnt -rn -M "$root" -o FSTYPE 2>/dev/null | grep -qx 'fuse.rclone'; then
          ready=0
          break
        fi
      done
      [ "$ready" -eq 1 ] && break
      sleep 2
    done
  else
    sleep 10
  fi

  if is_fuse_mount "$target"; then
    echo "Media Pool $slug montou automaticamente."
    continue
  fi

  echo "Media Pool $slug ainda não montou; aplicando recuperação direta pelo container."

  # Elimina somente uma tentativa órfã deste pool. Não toca nos mounts de Drive.
  pkill -f "rclone mount media_pool: ${target}" 2>/dev/null || true
  lazy_unmount "$target"
  mkdir -p "$target"

  docker exec "$CONTAINER" mkdir -p "$target" >/dev/null 2>&1 || true

  docker exec -d "$CONTAINER" \
    rclone mount media_pool: "$target" \
      --config="/data/media-pools/$slug/rclone.conf" \
      --read-only \
      --allow-other \
      --umask=002 \
      --dir-cache-time=10m \
      --vfs-cache-mode=off \
      --buffer-size=0 \
      --timeout=1m \
      --contimeout=15s \
      --low-level-retries=10 \
      --log-level=INFO \
      --log-file="/data/media-pools/$slug/mount.log" \
      >/dev/null 2>&1 || true

  ok=0
  for _ in $(seq 1 60); do
    if is_fuse_mount "$target"; then
      ok=1
      break
    fi
    sleep 2
  done

  if [ "$ok" -eq 1 ]; then
    echo "Media Pool $slug recuperado: $target (fuse.rclone)"
  else
    echo "AVISO: Media Pool $slug não montou; mantendo Gateway sem apontar para diretório vazio." >&2
    docker exec "$CONTAINER" sh -c "tail -n 40 '/data/media-pools/$slug/mount.log' 2>/dev/null || true" 2>/dev/null || true
  fi
done
