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

- `rclone-manager-unraid-v1.9.0.zip`
- `rclone-manager-desktop-zorinos-v1.5.0.zip`
- `rclone-manager-desktop-zorinos_1.5.0_all.deb`
- `rclone-manager-vps-v1.2.0.zip`
- `rclone-manager-vps-v1.2.0.tar.gz`
- `rclone-manager-drive-link-copier-v1.3.0.zip`
- `SHA256SUMS.txt`

## Publicação reproduzível e autocontida

O repositório contém `release-bundle/source-full/rclone-manager-bases-1.7.8.tar.xz`, snapshot das quatro bases validadas. SHA-256:

```text
b518ae51b5a87ce306fb6f000c042b9e5767ae52c26d4b0e020b0a263e819268
```

O delta final é reconstruído de `final-1.9.0-patches-small.b64.part-*`. SHA-256:

```text
8fcec580b4f5cbecc30120cd396f70af23931a2b91f9a490384a85e0a3b73a74
```

O Actions valida ambos, aplica os quatro patches, verifica versões, sintaxe Python e ausência de arquivos sensíveis, gera os pacotes e publica a Release. A reconstrução não depende de nenhuma GitHub Release anterior.

A publicação só é considerada concluída quando o verificador independente confirma os sete assets e registra `release-bundle/PUBLISHED-1.9.0.txt` no branch `main`. Cada execução do publicador também é registrada em `release-bundle/PUBLISH-RUN-1.9.0.txt`.

## Notas de quota

Service Accounts ajudam somente nos limites que podem ser distribuídos entre identidades. Limites de Shared Drive, proprietário de arquivo, organização ou outras políticas do Google não são removidos pelo Manager.
