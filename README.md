# Rclone Manager

Gerenciador de múltiplas contas Google Drive e importação de links/OneDrive para **Unraid**, **ZorinOS Desktop**, **Linux/VPS** e **Windows 10/11**, com extensão Chrome/Chromium integrada ao Manager.

## Versões atuais

| Edição | Versão | Status |
|---|---:|---|
| **Unraid** | **1.7.8** | **Stable** |
| **ZorinOS Desktop** | **1.3.8** | **Stable** |
| **Linux / VPS** | **1.0.9** | **Stable** |
| **Drive Link Copier (Chrome/Chromium)** | **1.2.3** | **Stable** |
| **Windows 10/11** | **1.1.2** | Beta |

## Download

Os downloads atuais ficam juntos em **uma única GitHub Release**:

**`rclone-manager-v1.7.8`**

Ela contém o ZIP do Unraid, ZIP e `.deb` do ZorinOS, ZIP e TAR.GZ da VPS, a extensão Drive Link Copier e `SHA256SUMS.txt`.

## Principais recursos

- múltiplas contas Google Drive;
- mounts via rclone/FUSE;
- Centro de Transferências entre Drives;
- acesso a **Compartilhados comigo**;
- importação OneDrive → Google Drive;
- fallback Microsoft Graph `/content` quando necessário;
- processamento econômico de disco: **download de um arquivo → upload confirmado → limpeza → próximo arquivo**;
- **Backup Completo Portátil v2** com banco, contas, rclone, credenciais OAuth/tokens e Microsoft/OneDrive;
- Centro de Upload com sessões resumíveis;
- Speedtest integrado com histórico;
- **Drive Link API v8** integrada à extensão;
- detecção de Google Drive, OneDrive/SharePoint, MediaFire, Dropbox, Pixeldrain e links HTTP/HTTPS diretos suportados;
- Google Drive → Google Drive via API oficial `files.copy`, sem armazenar o conteúdo localmente;
- confirmação do novo `fileId` e da pasta de destino antes de marcar sucesso;
- painel **API / Extensão** com origem, destino, progresso, tráfego, temporário e controles;
- pausa, retomada, cancelamento e exclusão de tarefas;
- **fila persistente FIFO** com prioridade por “Iniciar agora” e execução serial;
- **Tentar novamente** e retorno ao fim da fila para tarefas com erro corrigível;
- criação e exclusão de pastas Google Drive pela extensão;
- carregamento automático das pastas ao trocar a conta Google de destino;
- destino explicitamente confirmado antes de iniciar uma importação.

## Unraid 1.7.8

Atualização:

```bash
cd /mnt/user/appdata/rclone-manager
# extraia o pacote por cima preservando .env, data/ e cache/
chmod +x *.sh scripts/*.sh
./update.sh
```

## ZorinOS Desktop 1.3.8

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.3.8_all.deb
```

Os dados persistentes do usuário são preservados durante a atualização.

## Linux / VPS 1.0.9

Preparada para Ubuntu/Oracle Cloud com instalação padrão em `/opt/rclone-manager`.

```bash
cd /tmp
rm -rf rclone-vps-109
mkdir -p rclone-vps-109
cd rclone-vps-109
unzip /opt/rclone-manager-vps-v1.0.9.zip
cd rclone-manager-vps-v1.0.9
chmod +x install.sh update.sh rollback.sh backup.sh uninstall.sh
chmod +x scripts/*.sh
sudo ./install.sh
```

O instalador preserva `.env`, `data/`, `cache/` e `backups/` da instalação existente.

## Drive Link Copier 1.2.3

1. Extraia `rclone-manager-drive-link-copier-v1.2.3.zip`.
2. Abra `chrome://extensions` no Chrome/Chromium.
3. Ative **Modo do desenvolvedor** e escolha **Carregar sem compactação**.
4. Em **Configuração da extensão**, informe a URL HTTPS do Manager e a API Key gerada no Manager.

A extensão envia apenas os links/IDs e o destino escolhido. Credenciais Google, refresh tokens e Client Secrets permanecem no Manager.

## Backup Completo Portátil v2

O backup portátil pode incluir as configurações necessárias para restauração/migração, inclusive Google Drive, rclone, credenciais OAuth/tokens, Microsoft/OneDrive, banco e histórico.

**Atenção:** um backup completo contém credenciais e tokens sensíveis. Não publique nem compartilhe esse arquivo.

## Windows 10/11

A edição Windows continua em **1.1.2 Beta** até concluir a validação específica de mount/WinFsp e instalador em Windows real.

## Segurança

Este repositório **não inclui dados reais de instalação**: Client Secret, tokens OAuth, `rclone.conf`, bancos SQLite, `.env`, senhas, API Keys, webhooks ou backups.

Veja [SECURITY.md](SECURITY.md) e [docs/RELEASE-RCLONE-MANAGER-1.7.8.md](docs/RELEASE-RCLONE-MANAGER-1.7.8.md).
