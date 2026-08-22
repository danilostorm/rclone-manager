# Rclone Manager v1.9.0 — Release unificada

Release estável que consolida o **Media Pool / Drive Union** e o **Google Advanced Engine**.

## Versões incluídas

- **Unraid 1.9.0**
- **ZorinOS Desktop 1.5.0**
- **Linux/VPS 1.2.0**
- **Drive Link Copier 1.3.0**

Windows permanece em 1.1.2 Beta.

## Media Pool / Drive Union

- seleção de conta e navegação de pastas;
- inclusão de somente as bibliotecas desejadas;
- várias pastas da mesma conta;
- categorias virtuais compartilhadas entre contas;
- mount único para Jellyfin/Plex;
- armazenamento usado/livre agregado por conta;
- localizador físico de arquivos;
- status degradado quando uma origem falha;
- roteamento opcional de novos uploads;
- criação/remoção do Pool não move nem apaga arquivos do Google Drive.

## Google Advanced

- eclone preferencial, gclone opcional e Drive API como fallback;
- Service Accounts;
- Rolling SA;
- escolha inicial aleatória;
- preload;
- blacklist e anti-thrashing;
- cache de `about.storageQuota`;
- painel de usado/livre/total quando disponível.

## Assets oficiais

A release contém:

- `rclone-manager-unraid-v1.9.0.zip`
- `rclone-manager-desktop-zorinos-v1.5.0.zip`
- `rclone-manager-desktop-zorinos_1.5.0_all.deb`
- `rclone-manager-vps-v1.2.0.zip`
- `rclone-manager-vps-v1.2.0.tar.gz`
- `rclone-manager-drive-link-copier-v1.3.0.zip`
- `SHA256SUMS.txt`

## Publicação reproduzível

O workflow oficial reconstrói primeiro as bases estáveis históricas do próprio repositório e depois aplica o delta final armazenado em `release-bundle/source-full/`. O delta final possui SHA-256 fixado em `8fcec580b4f5cbecc30120cd396f70af23931a2b91f9a490384a85e0a3b73a74`.

Antes de publicar, o Actions verifica versões, sintaxe Python, integridade do delta, ausência de arquivos persistentes/sensíveis e integridade dos pacotes gerados. Depois da publicação, a lista de assets é conferida novamente.

## Notas de quota

Service Accounts ajudam somente nos limites que podem ser distribuídos entre identidades. Limites de Shared Drive, proprietário de arquivo, organização ou outras políticas do Google não são removidos pelo Manager.
