# Rclone Manager 1.4.0-rc11-ha4.7.3

Data: 2026-08-26

## Distribuição via Git

- `git-install.sh` instala/atualiza e configura um hook `post-merge` local.
- após a migração inicial, `git pull` aplica a nova versão automaticamente quando o checkout tem root ou sudo sem senha;
- `git-update.sh` continua disponível como modo explícito;
- um único payload atual em `dist/rclone-manager-current-base.tar.gz` é validado por SHA256;
- Unraid usa o payload base; VPS e Zorin aplicam somente seus overrides de instalação/Compose.

## Upload de pastas

- pasta inteira com nome raiz preservado;
- subpastas e diretórios vazios preservados;
- `showDirectoryPicker()` quando disponível e fallback `webkitdirectory`;
- drag-and-drop recursivo de diretórios;
- manifesto de diretórios enviado antes da fila de arquivos;
- upload resumível por chunks direto ao Google Drive;
- deduplicação, ETA agregado, repetir falhas e limpar concluídos.

## HA acumulado

Inclui HA4.7 Auto HA Integration, HA4.7.1 Cache Safe e HA4.7.2 Drive Isolation / Pool Degraded, além das correções anteriores de Controller/Witness/Gateway, stale FUSE e runtime reconcile.

## Zorin OS

A antiga distribuição desktop passa a usar o mesmo núcleo atual do Unraid/VPS via Docker Compose, serviço systemd, FUSE/rclone e launcher desktop local.
