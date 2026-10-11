# Recuperação automática do Media Gateway: AEROCOOL e Oracle

Novo watchdog independente do Docker, sem reiniciar Rclone Manager, Plex ou Jellyfin.

A verificação lê as bibliotecas e backends do MultiServer Agent em cada host.
Para backend local, só recupera se a origem FUSE estiver montada e tiver
pastas/arquivos reais; se a origem estiver vazia, não altera nada.
Para backend SFTP/SSH, pede recuperação ao Agent e não força binds locais.
A recuperação depende de 2 verificações consecutivas degradadas, a cada 90s,
com espera mínima de 10 minutos entre tentativas de recuperação da mesma biblioteca.

## AEROCOOL (Unraid)

    cd /mnt/user/appdata/rclone-manager-src
    git -c core.hooksPath=/dev/null pull --ff-only
    bash scripts/install-media-gateway-watchdog.sh --check
    bash scripts/install-media-gateway-watchdog.sh --install
    tail -n 60 /mnt/user/appdata/rclone-manager/data/media-gateway-watchdog/watchdog.log

A instalação registra o inicializador em /boot/config/go, com backup antes de
qualquer mudança e espera o array estar disponível ao iniciar após o reboot.

## Oracle (VPS)

    cd /opt/rclone-manager-src
    git -c core.hooksPath=/dev/null pull --ff-only
    bash scripts/install-media-gateway-watchdog.sh --check
    bash scripts/install-media-gateway-watchdog.sh --install
    systemctl status rclone-manager-media-watchdog --no-pager
    journalctl -u rclone-manager-media-watchdog -n 60 --no-pager

A instalação cria o serviço systemd, com Restart=always. Se não houver
bibliotecas configuradas na Oracle, aguarda sem criar montagens.

## Por que pular o hook post-merge?

O deploy normal do Rclone Manager desmonta mounts ao reconstruir o Docker.
O comando acima busca os novos scripts sem executar o hook; instalar apenas
o watchdog não provoca esse redeploy.

## Observações

- Não apaga arquivos, não elimina Media Pools nem altera bibliotecas Plex.
- Só tenta recuperar Gateway local quando a origem verdadeira foi verificada.
- Não soluciona ainda a causa interna de database is locked no SQLite.
  O monitor independente continua operando se uma thread interna morrer.
- Mudanças futuras no FUSE ainda exigem configuração correta de propagação
  no Docker (pasta-pai compartilhada no host e volume slave no Plex/Jellyfin).
- Para desligar na Oracle: systemctl disable --now rclone-manager-media-watchdog
- Para desativar no Unraid: retire a linha marcada RM_MEDIA_GATEWAY_WATCHDOG_V1
  de /boot/config/go e encerre o processo watchdog pelo terminal.
