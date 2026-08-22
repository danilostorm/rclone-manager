# Rclone Manager

Gerenciador de múltiplas contas Google Drive e importação OneDrive para **Unraid**, **ZorinOS Desktop**, **Linux/VPS** e **Windows 10/11**, com extensão Chrome/Chromium para detectar links Google Drive em páginas e enviá-los ao Manager.

## Versões atuais

| Edição | Versão | Status |
|---|---:|---|
| **Unraid** | **1.7.2** | **Stable** |
| **ZorinOS Desktop** | **1.3.2** | **Stable** |
| **Linux / VPS** | **1.0.3** | **Stable** |
| **Drive Link Copier (Chrome/Chromium)** | **1.0.1** | **Stable** |
| **Windows 10/11** | **1.1.2** | Beta |

## Download

A partir desta versão, os downloads atuais ficam juntos em **uma única GitHub Release**:

**`rclone-manager-v1.7.2`**

Ela contém o ZIP do Unraid, ZIP e `.deb` do ZorinOS, ZIP e TAR.GZ da VPS, a extensão Drive Link Copier e `SHA256SUMS.txt`.

## Principais recursos

- múltiplas contas Google Drive;
- mounts via rclone/FUSE;
- Centro de Transferências entre Drives;
- acesso a **Compartilhados comigo**;
- importação OneDrive → Google Drive, inclusive itens de **Compartilhados comigo**;
- fallback Microsoft Graph `/content` quando não há URL direta de download;
- processamento OneDrive arquivo por arquivo: download → upload confirmado → limpeza do temporário;
- retomada por checkpoint e tratamento de cota/retry;
- **Backup Completo Portátil v2**, incluindo banco, contas, rclone, credenciais OAuth/tokens e Microsoft/OneDrive;
- Centro de Upload com sessões resumíveis;
- Speedtest integrado com histórico;
- **Drive Link Copier** para detectar vários links Google Drive em páginas e copiar para uma conta/pasta escolhida no Manager;
- criação opcional de uma nova pasta para agrupar todos os links detectados;
- Google Drive → Google Drive via API oficial `files.copy`, com confirmação do novo `fileId` e validação da pasta de destino antes de marcar sucesso;
- no fluxo Drive → Drive, o conteúdo não precisa ser armazenado no disco local da VPS.

## Unraid 1.7.2

Atualização:

```bash
cd /mnt/user/appdata/rclone-manager
# extraia o pacote por cima preservando .env, data/ e cache/
chmod +x *.sh scripts/*.sh
./update.sh
```

## ZorinOS Desktop 1.3.2

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.3.2_all.deb
```

Os dados persistentes do usuário são preservados durante a atualização.

## Linux / VPS 1.0.3

Preparada para Ubuntu/Oracle Cloud com instalação padrão em `/opt/rclone-manager`.

```bash
cd /tmp
rm -rf rclone-vps-103
mkdir rclone-vps-103
cd rclone-vps-103
unzip /caminho/rclone-manager-vps-v1.0.3.zip
sudo ./install.sh
```

O instalador preserva `.env`, `data/`, `cache/` e `backups/` da instalação existente.

## Drive Link Copier 1.0.1

1. Extraia `rclone-manager-drive-link-copier-v1.0.1.zip`.
2. Abra `chrome://extensions` no Chrome/Chromium.
3. Ative **Modo do desenvolvedor** e escolha **Carregar sem compactação**.
4. Em **Configuração da extensão**, informe a URL HTTPS do Manager e a API Key gerada no menu **Configurações**.

A extensão apenas envia os IDs/links e o destino escolhido para o Manager. Credenciais Google, refresh tokens e Client Secrets permanecem no servidor/Manager.

## Backup Completo Portátil v2

O backup portátil pode incluir as configurações necessárias para restauração/migração, inclusive Google Drive, rclone, credenciais OAuth/tokens, Microsoft/OneDrive, banco e histórico.

**Atenção:** um backup completo contém credenciais e tokens sensíveis. Não publique nem compartilhe esse arquivo.

## Windows 10/11

A edição Windows continua em **1.1.2 Beta** até concluir a validação específica de mount/WinFsp e instalador em Windows real.

## Segurança

Este repositório **não inclui dados reais de instalação**: Client Secret, tokens OAuth, `rclone.conf`, bancos SQLite, `.env`, senhas, API Keys, webhooks ou backups.

O workflow da release unificada verifica arquivos sensíveis antes de montar os pacotes públicos.

Veja [SECURITY.md](SECURITY.md) e [docs/RELEASE-RCLONE-MANAGER-1.7.2.md](docs/RELEASE-RCLONE-MANAGER-1.7.2.md).
