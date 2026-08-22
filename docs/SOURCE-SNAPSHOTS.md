# Cadeia reproduzível de código-fonte — release 1.9.0

A release 1.9.0 pode ser reconstruída usando somente arquivos versionados neste repositório.

## Snapshot base autocontido

`release-bundle/source-full/rclone-manager-bases-1.7.8.tar.xz` reúne as quatro bases validadas usadas antes do delta final:

- Unraid `1.7.8`;
- ZorinOS Desktop `1.3.8`;
- VPS/Linux `1.0.9`;
- Drive Link Copier `1.2.3`.

SHA-256:

```text
b518ae51b5a87ce306fb6f000c042b9e5767ae52c26d4b0e020b0a263e819268
```

## Delta final 1.9.0

As partes `release-bundle/source-full/final-1.9.0-patches-small.b64.part-*` formam:

```bash
cat release-bundle/source-full/final-1.9.0-patches-small.b64.part-* \
  | base64 -d > final-1.9.0-patches.tar.xz
```

SHA-256:

```text
8fcec580b4f5cbecc30120cd396f70af23931a2b91f9a490384a85e0a3b73a74
```

O arquivo contém os quatro patches que produzem:

- Unraid `1.9.0`;
- ZorinOS Desktop `1.5.0`;
- VPS/Linux `1.2.0`;
- Drive Link Copier `1.3.0`.

O processo foi validado localmente aplicando os patches às bases e comparando as árvores reconstruídas com as árvores dos pacotes finais: não houve diferenças.

## GitHub Actions

`.github/workflows/publish-unified-release.yml`:

1. valida as versões esperadas;
2. valida o SHA-256 do snapshot base;
3. extrai as quatro bases;
4. reconstitui e valida o SHA-256 do delta final;
5. aplica os patches;
6. verifica versões, sintaxe Python e ausência de arquivos sensíveis;
7. gera os ZIPs/TAR.GZ/DEB;
8. gera `SHA256SUMS.txt`;
9. publica a GitHub Release;
10. confere novamente os sete assets publicados.

A 1.9.0 não depende de uma release antiga existir no GitHub e não depende dos patches históricos antigos que ficaram no repositório apenas para preservação de histórico.

Dados persistentes nunca fazem parte do snapshot: `.env`, `rclone.conf`, banco, tokens, JSONs de Service Account, chaves privadas, cache e backups.
