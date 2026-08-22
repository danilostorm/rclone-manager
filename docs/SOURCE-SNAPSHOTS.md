# Cadeia reproduzível de código-fonte — release 1.9.0

A release 1.9.0 é reconstruída inteiramente a partir do histórico versionado neste repositório.

## Bases estáveis

O workflow refaz as últimas bases publicadas usando os arquivos históricos já existentes:

- Unraid `1.7.8`;
- ZorinOS Desktop `1.3.8`;
- VPS/Linux `1.0.9`;
- Drive Link Copier `1.2.3`.

Essas bases derivam dos snapshots e patches históricos em `unraid-release/`, `desktop-release/`, `vps-release/` e `release-bundle/source/`.

## Delta final 1.9.0

`release-bundle/source-full/` contém o delta final dividido em partes Base64:

```text
final-1.9.0-patches-small.b64.part-00
...
final-1.9.0-patches-small.b64.part-15
```

Reconstrução:

```bash
cd release-bundle/source-full
cat final-1.9.0-patches-small.b64.part-* | base64 -d > final-1.9.0-patches.tar.xz
sha256sum final-1.9.0-patches.tar.xz
```

SHA-256 esperado:

```text
8fcec580b4f5cbecc30120cd396f70af23931a2b91f9a490384a85e0a3b73a74
```

O `.tar.xz` contém os patches que produzem exatamente:

- Unraid `1.9.0`;
- ZorinOS Desktop `1.5.0`;
- VPS/Linux `1.2.0`;
- Drive Link Copier `1.3.0`.

O processo foi validado localmente aplicando os quatro patches às bases correspondentes e comparando as árvores reconstruídas com as árvores dos pacotes finais: não houve diferenças.

## GitHub Actions

`.github/workflows/publish-unified-release.yml` executa a cadeia completa: reconstrói as bases, valida o SHA-256 do delta final, aplica os patches, verifica versões, sintaxe Python e ausência de arquivos sensíveis, gera os pacotes e publica a GitHub Release.

Dados persistentes de instalação nunca fazem parte da reconstrução: `.env`, `rclone.conf`, banco, tokens, JSONs de Service Account, chaves privadas, cache e backups.
