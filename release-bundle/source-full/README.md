# Source snapshots — Rclone Manager 1.9.0

Snapshots completos usados para reconstruir a GitHub Release oficial.

Reconstituição:

```bash
cat unraid-1.9.0.tar.xz.b64.part-* | base64 -d > unraid-1.9.0.tar.xz
cat desktop-1.5.0.tar.xz.b64.part-* | base64 -d > desktop-1.5.0.tar.xz
cat vps-1.2.0.tar.xz.b64.part-* | base64 -d > vps-1.2.0.tar.xz
cat drive-link-copier-1.3.0.tar.xz.b64.part-* | base64 -d > drive-link-copier-1.3.0.tar.xz
sha256sum -c SHA256SUMS-SOURCE.txt
```

Depois extraia o arquivo desejado com `tar -xJf`.
