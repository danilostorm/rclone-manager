# Rclone Manager — HA atual

Versão atual: **1.4.0-rc11-ha4.7.3**.

A árvore ativa foi simplificada em 2026-08-26. Patches, bundles e pipelines históricos foram retirados do `main`. A instalação atual usa um único payload versionado, dividido em partes pequenas e validado por SHA-256. Depois da primeira migração, a atualização normal é por `git pull`.

## O que está consolidado

- Google Drive / OneDrive, Transferências, Centro de Upload e Media Pools.
- MultiServer/HA com Controller, Agent, Gateway, Witness, failover e integração automática de hosts.
- `/media-union/<biblioteca>` como caminho estável.
- stale-FUSE auto-heal, runtime reconcile real e Drive Isolation/Pool Degraded.
- mounts read-only com VFS cache `off`, evitando cache de dezenas de GB por Drive.
- Upload de **pastas inteiras** preservando a pasta raiz e subpastas.
- Directory Picker moderno, fallback `webkitdirectory`, drag & drop recursivo e preservação de pastas vazias quando o navegador consegue enumerá-las.
- Retomada resumível, múltiplos uploads, repetição de falhas e limpeza de concluídos.
- Mesmo core atual para Unraid, Ubuntu/Debian/Oracle e Zorin OS.

## Primeira migração para Git

```bash
git clone https://github.com/danilostorm/rclone-manager.git ~/rclone-manager-src
cd ~/rclone-manager-src
./git-install.sh
```

O deploy preserva `.env`, banco, contas, tokens, Media Pools e estado HA. Antes de trocar o código ele gera backup em `backups/`.

## Atualizações seguintes

```bash
cd ~/rclone-manager-src
git pull --ff-only
```

O `post-merge` criado por `git-install.sh` aplica o novo payload automaticamente quando há root/sudo sem senha. Caso contrário, o próprio hook informa o comando `sudo` necessário.

## Integridade

`payload/current-source.tar.xz.b64.part-*` é concatenado e decodificado somente se o SHA-256 corresponder a `payload/current-source.tar.xz.sha256`. O workflow `validate-current.yml` executa a mesma verificação e valida Python, JavaScript, cache seguro, Upload de pastas e Pool degradado.
