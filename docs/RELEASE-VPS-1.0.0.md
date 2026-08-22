# Rclone Manager VPS v1.0.0

Primeira edição oficial para VPS Linux/Oracle Cloud, com instalação padrão em `/opt/rclone-manager`.

## Principais recursos

- base funcional do Unraid 1.6.9;
- importação OneDrive → Google Drive;
- suporte a **Compartilhados comigo**;
- correção CSRF da análise/importação OneDrive;
- fallback Microsoft Graph `/drives/{drive-id}/items/{item-id}/content` quando `@microsoft.graph.downloadUrl` não é retornado;
- download local completo antes do upload Google, com remoção do temporário somente após confirmação;
- retomada por `Range` e upload resumível;
- mounts rclone/FUSE, transferências, upload, backup/restore, diagnóstico e Speedtest;
- gerenciamento por systemd;
- dados persistentes em `/opt/rclone-manager`;
- mount root no host em `/mnt/rclone-manager-remotes`.

## Instalação

```bash
unzip rclone-manager-vps-v1.0.0.zip
cd rclone-manager-vps-v1.0.0
chmod +x install.sh
sudo ./install.sh
```

O instalador tenta instalar Docker, Docker Compose v2 e FUSE3 quando necessário em Ubuntu/Debian.

Recomendado usar HTTPS/reverse proxy e configurar a URL base no painel antes do OAuth Google/Microsoft.
