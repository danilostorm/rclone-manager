# Rclone Manager

Gerenciador de múltiplas contas Google Drive para **Unraid**, **ZorinOS Desktop** e **Windows 10/11**.

## Versões atuais

| Edição | Versão | Status |
|---|---:|---|
| **Unraid** | **1.6.9** | **Stable** |
| **ZorinOS Desktop** | **1.1.2** | **Stable** |
| **Windows 10/11** | **1.1.2** | Beta até validação final no Windows |

### Principais recursos

- múltiplas contas Google Drive;
- mounts via rclone/FUSE (e WinFsp na edição Windows);
- Centro de Transferências entre Drives;
- acesso a **Compartilhados comigo**;
- importação OneDrive → Google Drive, inclusive itens de **Compartilhados comigo**;
- fallback pelo endpoint Microsoft Graph `/content` quando a Microsoft não fornece URL direta de download;
- busca, criação de pastas, renomear e exclusão/lixeira;
- preferência por cópia Google → Google server-side;
- retomada por checkpoint;
- tratamento de cota e retry automático;
- estimativa de transferência nas últimas 24 horas;
- backup/restore e diagnóstico;
- **Centro de Upload** para enviar arquivos e pastas do computador diretamente aos Drives cadastrados;
- upload em blocos com sessão resumível do Google Drive;
- escolha do destino, criação de pasta, drag & drop, uploads simultâneos e tratamento de conflitos;
- uploads continuam ativos durante a navegação normal entre as telas do Manager;
- taxa instantânea e média de upload na fila e no histórico;
- **Speedtest** integrado com ping, jitter, download, upload e histórico de testes.

## Unraid

A versão estável é **1.6.9**. Baixe na seção **Releases** (`unraid-v1.6.9`).

Para atualizar uma instalação existente, extraia o conteúdo por cima de:

```text
/mnt/user/appdata/rclone-manager
```

Preserve obrigatoriamente:

```text
.env
data/
cache/
```

Depois execute:

```bash
cd /mnt/user/appdata/rclone-manager
chmod +x *.sh scripts/*.sh
./update.sh
```

## ZorinOS Desktop

A versão estável é **1.1.2**. Baixe o `.deb` na release **zorinos-v1.1.2** e instale/atualize com:

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.1.2_all.deb
```

Os dados locais do usuário são preservados durante a atualização.

Veja [docs/ZORINOS.md](docs/ZORINOS.md) e [docs/UPDATES.md](docs/UPDATES.md).

## Windows 10/11

A edição Windows está em **1.1.2 Beta** até concluir a validação específica de mount/WinFsp e instalador em Windows real. Ela não é promovida a Stable apenas por compartilhar o mesmo frontend das versões Linux.

## Segurança

Este repositório **não inclui dados reais de instalação**: Client Secret, tokens OAuth, `rclone.conf`, bancos SQLite, `.env`, senhas, webhooks ou backups.

Os workflows de release também verificam a presença de arquivos sensíveis antes de gerar os pacotes.

Veja [SECURITY.md](SECURITY.md).
