# Rclone Manager Desktop for ZorinOS v1.1.2

Versão estável validada em uso real no ZorinOS.

## Destaques

- upload continua ativo ao navegar entre os menus do Rclone Manager;
- taxa instantânea e média de upload na fila e no histórico;
- velocidade agregada para uploads simultâneos;
- novo menu **Speedtest** com ping, jitter, download e upload;
- perfis Rápido, Padrão e Completo;
- histórico persistente de Speedtests;
- mantém drag & drop, upload de pasta inteira, sessões resumíveis do Google Drive, tratamento de conflitos e histórico de uploads;
- mounts continuam read-only.

## Instalação / atualização

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.1.2_all.deb
```

Os dados locais do usuário são preservados durante a atualização.

## Segurança

O pacote não inclui `.env`, `rclone.conf`, banco de dados real, tokens OAuth, Client Secret, chaves privadas ou backups da instalação.
