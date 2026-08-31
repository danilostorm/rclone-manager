# Changelog

## 1.4.0-rc11-ha4.7.3.4 — 2026-08-31

- corrige VPS/Oracle onde o MultiServer Agent permanecia com versão antiga porque o serviço systemd não era sincronizado de forma confiável;
- `reconcile-agent-state.sh` agora sincroniza o Agent empacotado pelo deploy com o Agent vivo antes da reconciliação;
- descobre automaticamente o `EnvironmentFile` real da unit systemd e, se necessário, lê `MS_AGENT_TOKEN`, bind, porta e state dir diretamente do ambiente do processo;
- remove a dependência do caminho fixo `/opt/rclone-manager-multiserver-agent/agent.env`, que não existe em algumas instalações históricas;
- após eventual restart do Agent, aguarda o health e restaura as bibliotecas persistidas em `state.json` via `/v1/gateway/switch` com retry;
- evita o caso em que um restart manual/deploy deixa `/media-union/<biblioteca>` como diretório vazio mesmo com Drives/Media Pool saudáveis;
- mantém limpeza preventiva de FUSE stale, remount de Drives/Media Pools, AkiraBox/BuzzHeavier, metadados e VFS cache `off`.

## 1.4.0-rc11-ha4.7.3.3 — 2026-08-31

- corrige updates/recreates que deixavam processos `rclone mount` antigos vivos no host e mounts FUSE em `ENOTCONN`;
- o deploy Git agora limpa somente mounts gerenciados em `/mnt/rclone-manager-remotes` e stable paths em `/media-union` antes de subir a nova versão;
- Drives e Media Pools são remontados pelo Manager após o recreate;
- o MultiServer Agent é reiniciado e reconcilia automaticamente as bibliotecas persistidas em `state.json`, restaurando o Gateway/stable path com retry;
- um Drive realmente indisponível continua sendo tratado como `degraded` e não bloqueia o deploy;
- mantém a migração `live-source`, AkiraBox/BuzzHeavier, metadados de tamanho/extensão e VFS cache `off` das versões anteriores.

## 1.4.0-rc11-ha4.7.3.2 — 2026-08-31

- corrige a migração Git quando o payload empacotado está incompleto/truncado;
- hosts HA4.x já instalados passam a usar a própria instalação atual como fonte-base segura e o Git aplica somente o overlay novo;
- nenhuma produção é parada antes de validar fonte, overlay e `py_compile`;
- banco SQLite, OAuth/tokens, contas, Media Pools, cache e `.env` continuam preservados;
- mantém AkiraBox/BuzzHeavier e metadados de tamanho/extensão do HA4.7.3.1;
- o caminho de payload continua com SHA-256 + `xz -t` obrigatório para instalações sem uma base HA existente.

## 1.4.0-rc11-ha4.7.3.1 — 2026-08-31

- deploy via Git passa a aplicar um overlay idempotente antes do build;
- adiciona reconhecimento de AkiraBox (`akirabox.to`, `akirabox.com`) e BuzzHeavier (`buzzheavier.com`, `bzzhr.co`, `bzzhr.to`);
- adiciona resolução dos links externos antes do estágio download → upload;
- preserva `size_bytes`, `size_text` e extensão enviados pela extensão do navegador;
- Gerenciador de tarefas passa a expor tamanho total/conhecido e extensões quando disponíveis.

## 1.4.0-rc11-ha4.7.3 — 2026-08-26

- consolidação do estado atual do projeto em uma única versão Git;
- atualização por `git pull` com deploy pós-merge e backup antes da troca;
- remoção da árvore ativa de patches/releases/bundles/workflows históricos;
- Unraid, VPS Linux e Zorin OS passam a consumir o mesmo core;
- Controller HA, Witness lease, Gateway HA, instalador automático e integração automática de servidores;
- stale-FUSE auto-heal, gateway runtime reconcile e Drive Isolation/Pool Degraded;
- VFS cache `off` nos mounts read-only e limpeza do cache antigo;
- Centro de Upload atualizado para pasta inteira, preservação da raiz/subpastas, diretórios vazios quando detectáveis, Directory Picker, fallback `webkitdirectory`, drag/drop recursivo, retry e limpeza de concluídos;
- pipeline único para SHA-256, compile Python, sintaxe JavaScript e invariantes críticos.
