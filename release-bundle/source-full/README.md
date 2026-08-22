# Código-fonte reproduzível — Rclone Manager 1.9.0

Este diretório torna a release **1.9.0 autocontida** no próprio repositório.

## 1. Snapshot das bases validadas

`rclone-manager-bases-1.7.8.tar.xz` contém, sem dados persistentes de usuário:

- Unraid `1.7.8`;
- ZorinOS Desktop `1.3.8`;
- VPS/Linux `1.0.9`;
- Drive Link Copier `1.2.3`.

SHA-256:

```text
b518ae51b5a87ce306fb6f000c042b9e5767ae52c26d4b0e020b0a263e819268
```

## 2. Delta final

As partes `final-1.9.0-patches-small.b64.part-*` reconstituem o arquivo `final-1.9.0-patches.tar.xz`.

```bash
cat final-1.9.0-patches-small.b64.part-* | base64 -d > final-1.9.0-patches.tar.xz
sha256sum final-1.9.0-patches.tar.xz
```

SHA-256 esperado:

```text
8fcec580b4f5cbecc30120cd396f70af23931a2b91f9a490384a85e0a3b73a74
```

O delta contém:

- `unraid-1.7.8-to-1.9.0.patch`
- `desktop-1.3.8-to-1.5.0.patch`
- `vps-1.0.9-to-1.2.0.patch`
- `extension-1.2.3-to-1.3.0.patch`

O GitHub Actions valida os dois SHA-256, aplica os quatro patches, testa versões/sintaxe/arquivos sensíveis e somente então publica os pacotes finais.

Nenhuma GitHub Release antiga é necessária para reconstruir a 1.9.0.
