# RC11 — MultiServer / High Availability Foundation

## Objetivo

Transformar o Media Pool / Drive Union em uma arquitetura MultiServer com servidores conectados pela Tailscale, mantendo caminhos estáveis para Plex/Jellyfin independentemente do storage ativo.

## Regra de arquitetura

**Controller controla; Agent observa; Gateway serve. O Controller nunca fica no caminho do streaming.**

## Componentes

### MultiServer Controller

Integrado ao Rclone Manager. Mantém cadastro de nós, bibliotecas, prioridades, health state, eventos, failover e failback.

### MultiServer Agent

Serviço Python independente instalado em Unraid/Ubuntu/Oracle/outros Linux. Usa Bearer Token e escuta preferencialmente no IP Tailscale. Endpoints RC11:

- `GET /v1/health`
- `GET /v1/probe?path=...`
- `GET /v1/gateway/info`
- `POST /v1/gateway/backend/ensure`
- `POST /v1/gateway/switch`
- `POST /v1/gateway/unmount`

### Media Gateway

É o mesmo Agent em um nó com função Gateway. Mantém os mounts SFTP/rclone fora do processo web e publica caminhos estáveis em `/media-union/<biblioteca>` através de bind mounts read-only.

Exemplo:

- `/media-union/movies`
- `/media-union/series`
- `/media-union/animes`

Plex/Jellyfin nunca precisam conhecer IPs ou paths físicos dos storages.

## Banco

RC11 adiciona:

- `multiserver_nodes`
- `multiserver_libraries`
- `multiserver_members`
- `multiserver_events`

## Health check

O Controller monitora:

- Agent online/offline;
- latência;
- hostname/SO;
- Tailscale IP detectado;
- RAM/load;
- existência e legibilidade do path de storage;
- filesystem/mount source;
- espaço total/livre.

## Failover

Cada biblioteca possui Primary/Secondary/Backup, prioridade, threshold, cooldown e política de failover/failback.

Por segurança, failover automático em `ha_replica`, `primary_backup` e `hybrid` exige simultaneamente:

- nó online;
- path de storage saudável;
- `replica_state=ready`;
- `coverage >= 99.99`.

O Gateway RC11 é sempre read-only. Isso reduz risco de split-brain e evita que uploads/renames sejam gravados em dois primaries divergentes.

## Replicação

RC11 prepara o modelo de estado (`replica_state`, `coverage`, `generation`), mas **não executa sincronização automática de mídia**. Isso é intencional: a próxima etapa deve implementar manifesto/verificação antes de qualquer operação destrutiva.

### RC12 — Replica Engine planejado

- manifest incremental por path/size/mtime e hash seletivo;
- geração/versionamento por biblioteca;
- cálculo automático de coverage;
- fila persistente de replicação;
- sync/copy sem propagar delete imediatamente;
- tombstone/quarentena configurável;
- verificação antes de marcar `READY`;
- bandwidth windows e limites por Tailscale/site;
- re-sync após failback;
- auditoria e alertas.

## Testes RC11

- `py_compile` em todos os módulos alterados;
- parsing de 27 templates Jinja;
- migração SQLite RC10.1 → RC11 com `PRAGMA integrity_check=ok`;
- Agent real: `/v1/health`, `/v1/probe` e rejeição de token inválido;
- Controller real contra Agent local;
- teste de failover: Primary unhealthy → Secondary READY/100% promovido;
- validação de ZIP/TAR e patch;
- pacotes sem banco/cache/credenciais runtime.

## Limitação de validação

O ambiente de empacotamento não tem Flask instalado, então não houve boot completo da WebUI local. O data plane SFTP/bind mount precisa ser validado nos servidores reais com Tailscale, rclone, SSH e permissões dos paths físicos.
