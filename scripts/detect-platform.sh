#!/usr/bin/env bash
set -euo pipefail
if [ -f /etc/unraid-version ] || [ -d /boot/config/plugins ]; then echo unraid; exit 0; fi
if [ -r /etc/os-release ]; then
  . /etc/os-release
  if [ "${ID:-}" = "zorin" ] || echo "${NAME:-}" | grep -qi zorin; then echo zorin; exit 0; fi
fi
echo vps
