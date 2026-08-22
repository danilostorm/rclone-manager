# Snapshots de código-fonte da release 1.9.0

O diretório `release-bundle/source-full/` contém snapshots completos das quatro edições publicadas:

- `unraid-1.9.0.tar.xz.b64.part-*`
- `desktop-1.5.0.tar.xz.b64.part-*`
- `vps-1.2.0.tar.xz.b64.part-*`
- `drive-link-copier-1.3.0.tar.xz.b64.part-*`

As partes são texto Base64. Para reconstruir um snapshot localmente:

```bash
cat unraid-1.9.0.tar.xz.b64.part-* | base64 -d > unraid-1.9.0.tar.xz
sha256sum -c SHA256SUMS-SOURCE.txt
mkdir source-unraid
tar -xJf unraid-1.9.0.tar.xz -C source-unraid
```

O workflow de GitHub Actions executa o mesmo processo antes de empacotar a release oficial.

Esses snapshots **não contêm dados persistentes de instalação**: `.env`, banco, `rclone.conf`, tokens, JSONs de Service Account, chaves privadas, cache ou backups.
