# Rclone Manager

Gerenciador de múltiplas contas Google Drive criado para **Unraid** e **ZorinOS Desktop**.

## Versões estáveis

| Edição | Versão | Pacote |
|---|---:|---|
| **Unraid** | **1.4.0 Final** | `dist/unraid/rclone-manager-unraid-v1.4.0.zip` |
| **ZorinOS Desktop** | **1.0.0** | GitHub Releases + `dist/zorinos/` |

### Principais recursos

- múltiplas contas Google Drive;
- mounts via rclone/FUSE;
- Centro de Transferências entre Drives;
- acesso a **Compartilhados comigo**;
- busca, criação de pastas, renomear e exclusão/lixeira;
- preferência por cópia Google → Google server-side;
- retomada por checkpoint;
- tratamento de cota e retry automático;
- estimativa de transferência nas últimas 24 horas;
- backup/restore e diagnóstico.

## Unraid

Baixe `dist/unraid/rclone-manager-unraid-v1.4.0.zip`, extraia em:

```text
/mnt/user/appdata/rclone-manager
```

Depois:

```bash
cd /mnt/user/appdata/rclone-manager
chmod +x *.sh scripts/*.sh
./install.sh
```

Para atualizar uma instalação existente, preserve `.env`, `data/` e `cache/`, substitua os arquivos do pacote e rode:

```bash
./update.sh
```

## ZorinOS Desktop

Baixe o `.deb` na seção **Releases** e instale:

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.0.0_all.deb
```

Atualizações futuras usam o mesmo comando com o novo `.deb`; os dados locais do usuário são preservados.

Veja [docs/ZORINOS.md](docs/ZORINOS.md) e [docs/UPDATES.md](docs/UPDATES.md).

## Segurança

Este repositório **não inclui dados reais de instalação**: Client Secret, tokens OAuth, `rclone.conf`, bancos SQLite, `.env`, senhas, webhooks ou backups.

Veja [SECURITY.md](SECURITY.md).