# Rclone Manager Desktop no ZorinOS

## Instalação

Baixe o pacote `.deb` da release mais recente e rode:

```bash
sudo apt update
sudo apt install ./rclone-manager-desktop-zorinos_X.Y.Z_all.deb
```

Depois procure **Rclone Manager** no menu do ZorinOS.

## Dados locais

O pacote do aplicativo e os dados do usuário ficam separados. Atualizar o `.deb` não deve apagar os dados persistentes.

Diretórios usados pela edição Desktop:

```text
~/.local/share/rclone-manager-desktop/
~/.cache/rclone-manager-desktop/
~/RcloneDrives/
```

## Atualização

1. Baixe o novo `.deb` em Releases.
2. Faça um backup pelo próprio Rclone Manager quando desejar proteção adicional.
3. Instale por cima:

```bash
sudo apt install ./rclone-manager-desktop-zorinos_NOVA_VERSAO_all.deb
```

4. Abra o aplicativo e confirme os mounts e contas.

## Google OAuth

Use um projeto próprio no Google Cloud com **Google Drive API** ativada. Não compartilhe Client Secret nem tokens.

Para Desktop, o callback local usado pelo aplicativo é:

```text
http://127.0.0.1:8787/oauth/google/callback
```

## Desinstalação

```bash
sudo apt remove rclone-manager-desktop
```

Faça backup antes de qualquer limpeza manual dos diretórios de dados.