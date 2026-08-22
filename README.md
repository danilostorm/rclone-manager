# Rclone Manager

Gerenciador de múltiplas contas Google Drive, transferências, uploads e bibliotecas de mídia para **Unraid**, **ZorinOS Desktop** e **Linux/VPS**, com extensão Chrome/Chromium integrada.

## Versões atuais

| Edição | Versão | Status |
|---|---:|---|
| **Unraid** | **1.9.0** | Stable |
| **ZorinOS Desktop** | **1.5.0** | Stable |
| **Linux / VPS** | **1.2.0** | Stable |
| **Drive Link Copier** | **1.3.0** | Stable |
| **Windows 10/11** | **1.1.2** | Beta |

A release unificada é **`rclone-manager-v1.9.0`**.

## Destaques da 1.9.0

### Media Pool / Drive Union para Jellyfin e Plex

O Manager pode reunir pastas de várias contas Google em um único mount virtual, sem mover nem copiar o conteúdo original.

Fluxo:

```text
Conta Anime 01 ── pasta /Animes ──┐
Conta Anime 02 ── pasta /Animes ──┤
Conta Filmes   ── pasta /Filmes ──┤
Conta Séries   ── pasta /Series ──┘
                                  ↓
                         Media Pool / Union
                                  ↓
                  /mnt/.../_media-pools/stormflix
                                  ↓
                         Jellyfin / Plex
```

Recursos:

- seleção de conta e navegação por pastas antes de adicionar ao Pool;
- múltiplas pastas da mesma conta;
- categorias virtuais como `Animes`, `Filmes`, `Series` e `Desenhos`;
- várias origens podem compartilhar a mesma categoria;
- único ponto de montagem para Jellyfin/Plex;
- status por origem e estado degradado quando uma origem falha;
- espaço usado/livre agregado quando a API do Google fornece cota;
- localizador de arquivo para descobrir a conta/pasta física;
- roteamento opcional de novos uploads por categoria e espaço livre;
- o roteamento de upload **não participa do streaming** e pode ficar desativado em bibliotecas somente leitura.

Detalhes: [docs/MEDIA-POOL.md](docs/MEDIA-POOL.md).

### Google Advanced: eclone / gclone + Service Accounts

O Manager integra um motor Google avançado para cópias e operações server-side. Quando configurado, prefere **eclone**, aceita **gclone** como fallback e mantém a Drive API como fallback final.

Inclui:

- rotação de Service Accounts;
- Rolling SA;
- escolha inicial aleatória;
- preload de serviços;
- blacklist temporária após limite;
- anti-thrashing;
- cache de `about.storageQuota`;
- usado/livre/total por conta quando disponível.

O eclone é um projeto terceiro e é baixado do repositório upstream configurado pelo Manager; não é incorporado ao código deste repositório.

Detalhes e limitações: [docs/GOOGLE-ADVANCED-ECLONE.md](docs/GOOGLE-ADVANCED-ECLONE.md).

## Outros recursos

- múltiplas contas Google Drive;
- mounts via rclone/FUSE;
- Centro de Transferências entre Drives;
- acesso a **Compartilhados comigo**;
- importação OneDrive/SharePoint → Google Drive;
- fallback Microsoft Graph `/content`;
- download por arquivo, upload confirmado e limpeza do temporário;
- Backup Completo Portátil v2;
- Centro de Upload com sessões resumíveis;
- Speedtest com histórico;
- Drive Link API integrada à extensão;
- Google Drive → Google Drive via API oficial `files.copy` quando aplicável;
- fila persistente, pausa, retomada, cancelamento e retry;
- Google Advanced Engine com eclone/gclone e Service Accounts.

## Código-fonte e reprodução da release

A release estável é reproduzível a partir do próprio histórico Git. As bases anteriores permanecem versionadas em `unraid-release/`, `desktop-release/`, `vps-release/` e `release-bundle/source/`. O diretório `release-bundle/source-full/` contém o delta final validado da 1.9.0, dividido em partes Base64 e protegido por SHA-256.

O workflow `.github/workflows/publish-unified-release.yml` reconstrói as bases, valida o delta final, aplica os patches, checa versões, sintaxe e arquivos sensíveis, empacota cada edição e publica a GitHub Release. O código completo de cada edição também fica dentro dos ZIPs/TAR.GZ publicados.

Veja [docs/SOURCE-SNAPSHOTS.md](docs/SOURCE-SNAPSHOTS.md) para a cadeia completa de reconstrução.

## Atualização

### VPS / Oracle Cloud

```bash
cd /opt
unzip -q rclone-manager-vps-v1.2.0.zip
cd rclone-manager-vps-v1.2.0
sudo ./install.sh
```

A instalação padrão é `/opt/rclone-manager` e o instalador preserva `.env`, `data/`, `cache/` e `backups/`.

### Unraid

Extraia o ZIP por cima de `/mnt/user/appdata/rclone-manager`, preservando `.env`, `data/` e `cache/`, e execute:

```bash
cd /mnt/user/appdata/rclone-manager
chmod +x *.sh scripts/*.sh
./update.sh
```

### ZorinOS Desktop

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.5.0_all.deb
```

Veja [docs/UPDATES.md](docs/UPDATES.md) para rollback e verificações.

## Segurança

Este repositório não deve conter dados reais de instalação, incluindo `.env`, Client Secret, tokens OAuth, `rclone.conf`, bancos SQLite, JSONs de Service Account, chaves privadas, API Keys ou backups.

Veja [SECURITY.md](SECURITY.md).

## Terceiros

- [rclone](https://github.com/rclone/rclone)
- [eclone](https://github.com/ebadenes/eclone)
- gclone, quando instalado separadamente pelo operador

O uso e a distribuição de cada componente terceiro seguem as respectivas licenças upstream.
