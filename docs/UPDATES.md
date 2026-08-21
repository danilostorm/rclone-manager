# Atualizações e releases

## Unraid

A edição Unraid usa versões `1.x.y` e a versão estável atual é `1.4.0 Final`.

Para atualização manual:

```bash
cd /mnt/user/appdata/rclone-manager
# substitua apenas arquivos de código/pacote
# preserve .env, data/ e cache/
./update.sh
```

## ZorinOS

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

### Checklist antes de publicar

1. Atualizar a versão em `desktop-release/VERSION`.
2. Gerar o ZIP limpo da edição Desktop.
3. Confirmar que não existem `.env`, `rclone.conf`, tokens ou bancos reais.
4. Atualizar `CHANGELOG.md`.
5. Fazer push no `main`.

O workflow `publish-zorinos-release.yml` monta o `.deb`, calcula SHA256 e cria/atualiza a GitHub Release automaticamente.