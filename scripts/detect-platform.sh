#!/usr/bin/env bash
set -euo pipefail
if [ -f /etc/unraid-version ] || [ -d /boot/config/plugins ]; then
  echo unraid
  exit 0
fi
if [ -r /etc/os-release ]; then
  . /etc/os-release
  case "${ID:-}" in
    zorin) echo zorin; exit 0;;
  esac
fi
echo vps
