# Rclone Manager for Unraid v1.7.0

## Backup Completo Portátil v2

Esta versão adiciona backup e restauração portátil da configuração completa do Rclone Manager, incluindo contas Google Drive, configurações do rclone, credenciais OAuth, tokens, Microsoft/OneDrive, banco de dados, histórico e preferências do painel.

Cache, arquivos temporários, conteúdo dos mounts e arquivos armazenados nos Drives não entram no backup.

> O backup contém credenciais e tokens sensíveis. Guarde o arquivo em local seguro.

## OneDrive → Google Drive

Mantém as correções validadas para **Compartilhados comigo**, fallback Microsoft Graph `/content`, retomada de downloads e o fluxo seguro arquivo por arquivo: download local → upload confirmado no Google → limpeza do temporário.

## Atualização

Preserve `.env`, `data/` e `cache/`, extraia por cima de `/mnt/user/appdata/rclone-manager` e execute:

```bash
cd /mnt/user/appdata/rclone-manager
chmod +x *.sh scripts/*.sh
./update.sh
```
