# Rclone Manager for Unraid v1.5.2

Versão estável do Rclone Manager para Unraid.

## Destaques

- upload continua ativo durante a navegação normal entre as páginas do Manager;
- taxa instantânea e média de upload na fila e no histórico;
- velocidade agregada para uploads simultâneos;
- novo menu **Speedtest** com ping, jitter, download e upload;
- perfis Rápido, Padrão e Completo;
- histórico persistente de Speedtests;
- mantém Centro de Upload, uploads resumíveis do Google Drive, upload de pastas, drag & drop, tratamento de conflitos e estimativa de cota;
- mounts continuam somente leitura; operações de escrita permanecem restritas ao Manager.

## Atualização

Extraia o conteúdo da versão por cima de:

```text
/mnt/user/appdata/rclone-manager
```

Preserve:

```text
.env
data/
cache/
```

Depois execute:

```bash
cd /mnt/user/appdata/rclone-manager
chmod +x *.sh scripts/*.sh
./update.sh
```

## Segurança

O pacote não inclui `.env`, `rclone.conf`, banco de dados real, tokens OAuth, Client Secret, chaves privadas ou backups da instalação.
