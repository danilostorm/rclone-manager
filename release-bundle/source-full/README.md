# Cadeia de código-fonte — Rclone Manager 1.9.0

Este diretório contém o **delta final validado** que transforma as últimas bases estáveis publicadas nas versões finais da release 1.9.0.

Bases usadas:

- Unraid `1.7.8` -> `1.9.0`
- ZorinOS Desktop `1.3.8` -> `1.5.0`
- VPS/Linux `1.0.9` -> `1.2.0`
- Drive Link Copier `1.2.3` -> `1.3.0`

As bases anteriores continuam reproduzíveis pelos arquivos históricos já versionados em `unraid-release/`, `desktop-release/`, `vps-release/` e `release-bundle/source/`.

## Reconstruir o delta final

```bash
cat final-1.9.0-patches-small.b64.part-* | base64 -d > final-1.9.0-patches.tar.xz
sha256sum final-1.9.0-patches.tar.xz
```

SHA-256 esperado:

```text
8fcec580b4f5cbecc30120cd396f70af23931a2b91f9a490384a85e0a3b73a74
```

O arquivo contém quatro patches:

```text
unraid-1.7.8-to-1.9.0.patch
desktop-1.3.8-to-1.5.0.patch
vps-1.0.9-to-1.2.0.patch
extension-1.2.3-to-1.3.0.patch
```

O workflow `.github/workflows/publish-unified-release.yml` reconstrói primeiro as quatro bases estáveis a partir do histórico do próprio repositório, valida o SHA-256 deste delta, aplica os patches e só então gera os assets da GitHub Release.

Nenhuma credencial, `.env`, `rclone.conf`, banco, JSON de Service Account, chave privada, cache ou backup faz parte desta cadeia de código-fonte.
