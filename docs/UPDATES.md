# Atualizações e releases

## Unraid

A edição Unraid usa versões `1.x.y` e a versão estável atual é **1.5.1**.

Para atualização manual:

```bash
cd /mnt/user/appdata/rclone-manager
# substitua apenas arquivos de código/pacote
# preserve .env, data/ e cache/
./update.sh
```

A release oficial usa a tag:

```text
unraid-vX.Y.Z
```

O workflow `.github/workflows/publish-unraid-release.yml` reconstrói o pacote a partir da base versionada e do patch da versão, executa verificação de arquivos sensíveis, gera SHA256 e publica a Release.

## ZorinOS

A versão estável atual é **1.1.1**.

A edição Desktop é publicada com tags:

```text
zorinos-vX.Y.Z
```

O release deve conter no mínimo:

```text
rclone-manager-desktop-zorinos_X.Y.Z_all.deb
rclone-manager-desktop-zorinos_X.Y.Z_all.deb.sha256
rclone-manager-desktop-zorinos-vX.Y.Z.zip
rclone-manager-desktop-zorinos-vX.Y.Z.sha256
```

O workflow `.github/workflows/publish-zorinos-release.yml` monta o pacote fonte, verifica se não há arquivos sensíveis, gera o `.deb`, calcula SHA256 e cria/atualiza a GitHub Release.

### Checklist antes de publicar

1. Atualizar o código/patch da edição correspondente.
2. Confirmar que não existem `.env`, `rclone.conf`, tokens, bancos reais, chaves privadas ou backups no pacote.
3. Atualizar `CHANGELOG.md` e as release notes.
4. Atualizar `desktop-release/VERSION` para ZorinOS ou `unraid-release/VERSION` para Unraid.
5. Fazer push no `main` e verificar a Release gerada pelo GitHub Actions.

## Windows

A edição Windows segue como **Beta** até passar pela validação específica em Windows 10/11, incluindo WinFsp, mount, inicialização e instalador. Só depois deve receber tag de Stable.
