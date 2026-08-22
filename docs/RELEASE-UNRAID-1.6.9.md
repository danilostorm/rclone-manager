# Rclone Manager for Unraid v1.6.9

## OneDrive → Google Drive

- corrige o token CSRF da análise/importação OneDrive;
- mantém a navegação de **Compartilhados comigo**;
- quando a Microsoft não fornece `@microsoft.graph.downloadUrl`, usa o endpoint oficial `/drives/{drive-id}/items/{item-id}/content` e segue o redirect `Location`;
- mantém retomada por `Range` na URL temporária real do OneDrive;
- preserva o fluxo seguro: download local completo → upload para o Google Drive → confirmação → limpeza do temporário.

## Atualização

Preserve obrigatoriamente `.env`, `data/` e `cache/`. Extraia o pacote por cima de `/mnt/user/appdata/rclone-manager` e execute:

```bash
cd /mnt/user/appdata/rclone-manager
chmod +x *.sh scripts/*.sh
./update.sh
```
