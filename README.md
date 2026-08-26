# Rclone Manager

Rclone Manager é um painel web para Google Drive/rclone, Media Pools, transferências, upload direto e MultiServer/High Availability.

## Versão atual

**1.4.0-rc11-ha4.7.3** — distribuição por Git + Upload de Pastas + HA4.7/Drive Isolation.

A árvore antiga de releases continua no repositório por compatibilidade, mas novas instalações e atualizações devem usar o fluxo Git abaixo.

## Instalação e atualização por Git

Clone o repositório em um diretório de código separado dos dados persistentes:

```bash
git clone https://github.com/danilostorm/rclone-manager.git rclone-manager-src
cd rclone-manager-src
sudo ./git-install.sh
```

O instalador detecta automaticamente **Unraid**, **VPS Ubuntu/Debian** ou **Zorin OS** e preserva `.env`, banco, OAuth, contas, cache/configuração e Media Pools existentes.

Depois da primeira instalação Git, o checkout recebe um `post-merge` local. Nas máquinas com root ou `sudo -n`, uma atualização futura pode ser feita simplesmente com:

```bash
git pull
```

Também existe o modo explícito:

```bash
./git-update.sh
```

### Caminhos recomendados

- Unraid: checkout em `/mnt/user/appdata/rclone-manager-src`; dados em `/mnt/user/appdata/rclone-manager`.
- VPS/Oracle: checkout em `/opt/rclone-manager-src`; dados em `/opt/rclone-manager`.
- Zorin OS: checkout em `/opt/rclone-manager-src`; dados em `/opt/rclone-manager`.

## Release empacotada atual

O Git contém o payload completo atual em `dist/rclone-manager-current-base.tar.gz`. O deploy valida SHA256 e usa o mesmo núcleo para as três plataformas, aplicando somente os overrides em `platform/vps` ou `platform/zorin`. Isso evita três cópias quase idênticas do aplicativo.

## Upload de pastas — HA4.7.3

A tela **Upload** aceita arquivos e pastas completas:

- botão **Pasta inteira** usando `showDirectoryPicker` quando suportado;
- fallback `webkitdirectory` em Chrome/Edge;
- arrastar uma pasta para a área de upload percorre subpastas recursivamente;
- preserva o **nome da pasta raiz**, subpastas e pastas vazias;
- seleção mista de arquivos e diretórios;
- deduplicação da fila;
- upload resumível por chunks direto ao Google Drive;
- ETA e taxa agregada;
- `Repetir falhas` e `Limpar concluídos`;
- conflito configurável: substituir, renomear ou ignorar;
- até 4 uploads simultâneos;
- roteamento por Media Pool para a conta com melhor espaço livre conhecido.

## MultiServer / HA

A linha HA atual inclui:

- Storage HA e Media Pool estável em `/media-union/<biblioteca>`;
- Gateway HA com múltiplos candidatos;
- Controller HA com Witness independente e lease anti split-brain;
- instalador automático de novos nós por SSH (senha ou chave privada);
- upgrade/reinstalação inteligente e porta automática;
- Tailscale/tailnet validation;
- auto-integração de novos Storage/Gateway às bibliotecas;
- runtime reconcile real (`mountpoint` + legibilidade);
- stale FUSE auto-heal;
- Drive Isolation: um remote quebrado deixa o Pool `degraded` sem derrubar os demais;
- VFS cache read-only em `off` para evitar consumo de dezenas de GB por Drive.

## Zorin OS

A antiga linha Desktop estava defasada. A partir desta versão o Zorin usa o mesmo núcleo atual do VPS/Unraid, via Docker Compose, com serviço systemd, FUSE/rclone e atalho de desktop para `http://127.0.0.1:8787`.

## Segurança

Não publique `.env`, bancos, tokens OAuth, chaves SSH privadas ou backups de dados no Git. Esses itens permanecem fora dos pacotes e são preservados localmente durante updates.
