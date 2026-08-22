# Rclone Manager Desktop for ZorinOS v1.3.0

## Backup Completo Portátil v2

Novo backup/restauração portátil com banco de dados, contas Google Drive, configurações do rclone, credenciais OAuth e tokens, configuração Microsoft/OneDrive, histórico e preferências do aplicativo.

Cache, temporários, mounts e conteúdo armazenado nos Drives não são incluídos.

> O arquivo de backup contém credenciais e tokens sensíveis. Armazene-o com segurança.

## OneDrive

Mantém a importação validada de **Compartilhados comigo**, fallback Microsoft Graph `/content`, retomada e limpeza do cache somente após confirmação do upload no Google Drive.

## Instalação / atualização

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.3.0_all.deb
```

Os dados persistentes do usuário são preservados durante a atualização.
