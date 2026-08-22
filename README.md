# Rclone Manager

Gerenciador de múltiplas contas Google Drive e importação OneDrive para **Unraid**, **ZorinOS Desktop**, **Linux/VPS** e **Windows 10/11**.

## Versões atuais

| Edição | Versão | Status |
|---|---:|---|
| **Unraid** | **1.7.0** | **Stable** |
| **ZorinOS Desktop** | **1.3.0** | **Stable** |
| **Linux / VPS** | **1.0.1** | **Stable** |
| **Windows 10/11** | **1.1.2** | Beta |

### Principais recursos

- múltiplas contas Google Drive;
- mounts via rclone/FUSE;
- Centro de Transferências entre Drives;
- acesso a **Compartilhados comigo**;
- importação OneDrive → Google Drive, inclusive itens de **Compartilhados comigo**;
- fallback Microsoft Graph `/content` quando não há URL direta de download;
- processamento OneDrive arquivo por arquivo: download → upload confirmado → limpeza do temporário;
- retomada por checkpoint e tratamento de cota/retry;
- **Backup Completo Portátil v2**, incluindo banco, contas, rclone, credenciais OAuth/tokens e Microsoft/OneDrive;
- busca, criação de pastas, renomear e exclusão/lixeira;
- Centro de Upload com sessões resumíveis;
- Speedtest integrado com histórico.

## Unraid

Versão estável: **1.7.0**. Release: `unraid-v1.7.0`.

Atualização:

```bash
cd /mnt/user/appdata/rclone-manager
# extraia o pacote por cima preservando .env, data/ e cache/
chmod +x *.sh scripts/*.sh
./update.sh
```

## ZorinOS Desktop

Versão estável: **1.3.0**. Release: `zorinos-v1.3.0`.

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.3.0_all.deb
```

Os dados persistentes do usuário são preservados durante a atualização.

## Linux / VPS

Versão estável: **1.0.1**. Release: `vps-v1.0.1`.

Preparada para Ubuntu/Oracle Cloud com instalação padrão em `/opt/rclone-manager`:

```bash
unzip rclone-manager-vps-v1.0.1.zip
cd rclone-manager-vps-v1.0.1
chmod +x install.sh
sudo ./install.sh
```

## Backup Completo Portátil v2

Unraid e ZorinOS podem gerar um backup portátil contendo as configurações necessárias para restauração/migração, inclusive Google Drive, rclone, credenciais OAuth/tokens, Microsoft/OneDrive, banco e histórico. A edição VPS v1.0.1 é compatível com a restauração desse formato.

**Atenção:** o arquivo de backup contém credenciais e tokens sensíveis. Não publique nem compartilhe esse arquivo.

## Windows 10/11

A edição Windows continua em **1.1.2 Beta** até concluir a validação específica de mount/WinFsp e instalador em Windows real.

## Segurança

Este repositório **não inclui dados reais de instalação**: Client Secret, tokens OAuth, `rclone.conf`, bancos SQLite, `.env`, senhas, webhooks ou backups.

Os workflows de release verificam a presença de arquivos sensíveis antes de gerar os pacotes.

Veja [SECURITY.md](SECURITY.md).
