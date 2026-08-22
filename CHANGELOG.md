# Changelog

## Release unificada 1.9.0 — Unraid 1.9.0 / ZorinOS 1.5.0 / VPS 1.2.0 / Extensão 1.3.0

- promove o **Media Pool / Drive Union** para Stable;
- permite selecionar conta, navegar por pastas e adicionar somente as bibliotecas desejadas;
- permite várias pastas da mesma conta no mesmo Pool;
- une pastas de contas diferentes por categoria virtual;
- entrega um único mount para Jellyfin/Plex;
- adiciona cota usada/livre/total por conta quando a Drive API fornece esses dados;
- agrega armazenamento no Pool sem contar a mesma conta várias vezes;
- adiciona localizador físico de arquivo;
- adiciona roteamento opcional de novos uploads por categoria, prioridade e espaço livre;
- deixa explícito que o roteamento de upload não participa do streaming;
- integra Google Advanced Engine com eclone/gclone + Service Accounts;
- adiciona Rolling SA, escolha inicial aleatória, preload, blacklist e anti-thrashing;
- mantém fallback para Google Drive API;
- publica snapshots completos e verificáveis em `release-bundle/source-full/` e passa a reconstruir a release diretamente deles;
- preserva importação OneDrive/SharePoint, Centro de Upload, Transferências, Backup Portátil, Speedtest e Drive Link API.

## Release unificada 1.7.8

- correções acumuladas de fila, retry, gerenciamento de pastas e Google Drive avançado anteriores ao Media Pool;
- versões: Unraid 1.7.8, ZorinOS 1.3.8, VPS 1.0.9 e extensão 1.2.3.

## Release unificada 1.7.2

- reúne Unraid, ZorinOS, VPS e Drive Link Copier em uma única GitHub Release;
- Google Drive -> Google Drive via API `files.copy` com confirmação do novo `fileId`;
- mantém Backup Completo Portátil v2, OneDrive compartilhado, upload, transferências e Speedtest.

Histórico detalhado das versões anteriores permanece nos documentos existentes em `docs/` e nas árvores de release legadas.
