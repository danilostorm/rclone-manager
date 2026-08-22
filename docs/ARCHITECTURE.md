# Arquitetura

## Camadas principais

```text
                    Rclone Manager
                         |
        +----------------+----------------+
        |                                 |
   Media Engine                       Copy Engine
        |                                 |
 rclone mount/union/combine          eclone/gclone/API
        |                                 |
 Media Pool para Jellyfin/Plex       Service Accounts
```

## Media Engine

Responsável por mounts e leitura de bibliotecas. O Media Pool combina origens sem transferir os arquivos entre contas.

## Copy Engine

Responsável por transferências e operações server-side. Pode usar eclone/gclone + Service Accounts quando configurado.

## Persistência

Dados de runtime ficam fora do código versionado:

- `.env`;
- banco SQLite;
- tokens OAuth;
- `rclone.conf`;
- JSONs de Service Account;
- cache;
- temporários;
- backups.

Esses arquivos não são publicados em GitHub Releases nem nos snapshots de código.
