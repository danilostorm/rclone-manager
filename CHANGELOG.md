# Changelog

## 1.4.0-rc11-ha4.7.3.12 — 2026-08-31

- aplica o layout fluido em todas as telas do painel, aproveitando melhor a largura disponível no desktop;
- adiciona tratamento global para tabelas largas com rolagem horizontal somente quando necessário;
- otimiza grids, cabeçalhos, formulários e conteúdo longo para resoluções menores;
- adiciona navegação mobile off-canvas com botão de menu, backdrop e fechamento por link/Esc;
- em celulares, o conteúdo passa a ocupar 100% da tela e os grids são reduzidos progressivamente para duas e depois uma coluna;
- o overlay global é aplicado automaticamente no AEROCOOL e Oracle/VPS pelo fluxo normal de `git pull --ff-only`.

## 1.4.0-rc11-ha4.7.3.11 — 2026-08-31

- corrige o corte horizontal da tela **API / Extensão**, principalmente a coluna **AÇÕES** no Oracle/VPS;
- adiciona overlay idempotente que mantém o conteúdo principal dentro do viewport e cria rolagem horizontal somente na tabela quando necessário;
- redistribui as sete colunas da fila e reserva largura real para os botões de ação, preservando o layout em telas menores;
- o overlay é aplicado automaticamente em hosts HA existentes pelo fluxo `git pull --ff-only` / `deploy-current.sh`.

## 1.4.0-rc11-ha4.7.3.10 — 2026-08-31

- expande links de lista do Pixeldrain pela API pública antes de enfileirar os itens;
- integra o overlay de listas Pixeldrain ao deploy Git atual, inclusive em instalações HA existentes.

## 1.4.0-rc11-ha4.7.3.9 — 2026-08-31

- corrige `name 'urlsplit' is not defined` no resolver BuzzHeavier em bases HA antigas;
- o overlay agora garante de forma idempotente os imports `urljoin`, `urlsplit` e `urlunsplit` antes de ativar fallback/mirrors;
- mantém suporte a `HX-Redirect` e `Location` para seguir a URL final retornada pelo endpoint `/download`.

## 1.4.0-rc11-ha4.7.3.8 — 2026-08-31

- adiciona headers de navegador e fallback automático entre `buzzheavier.com`, `bzzhr.co` e `bzzhr.to`;
- preserva cookies da página e envia `HX-Request`, `HX-Current-URL` e `Referer` ao endpoint `/download`;
- segue `HX-Redirect`/`Location` retornado pelo BuzzHeavier antes do estágio de download.

## 1.4.0-rc11-ha4.7.3.7 — 2026-08-31

- adiciona histórico persistente por link para a extensão, independente da limpeza do histórico visual de tarefas;
- cada item é registrado somente depois de uma cópia/upload concluído com sucesso;
- novo endpoint `POST /api/v1/extension/history/check` (`drive-link-v13`) informa se o link já foi importado, destino, tarefa e data da última importação;
- o histórico é retroalimentado automaticamente a partir de tarefas antigas com `completed_items > 0`, aproveitando downloads já concluídos antes desta versão;
- normaliza Google Drive por ID, remove parâmetros de rastreamento e trata `href.li`/Dropbox para reduzir falsos negativos;
- adiciona `scripts/deploy-current.sh` para aplicar overlays atuais à fonte live antes do deploy Git validado;
- `git-install.sh` e `git-update.sh` passam a usar esse wrapper, preservando o fluxo simples `git pull --ff-only` após uma reinstalação única do hook;
- extensão v1.9.0 marca **JÁ BAIXADO**, pergunta se deseja baixar novamente e troca o bloco verde grande por uma barra compacta de servidor/versão.

## 1.4.0-rc11-ha4.7.3.6 — 2026-08-31

- corrige corrida de startup em que os Drives já voltavam como `fuse.rclone`, mas o Media Pool permanecia desmontado e `/media-union` ficava vazio;
- adiciona `scripts/recover-media-pools.sh`, que espera os Drives-base, valida cada Media Pool e, se necessário, remonta diretamente pelo container com os mesmos parâmetros read-only/VFS cache `off` usados pelo Manager;
- a recuperação de Media Pools roda antes da reconciliação do MultiServer Agent;
- Gateway local só é ativado quando a origem do Media Pool é realmente `fuse.rclone`, evitando bind de diretório vazio;
- mantém sincronização automática do Agent, descoberta dinâmica de token/env, limpeza de FUSE stale, Drive Isolation, AkiraBox/BuzzHeavier e metadados de tamanho/extensão.

## 1.4.0-rc11-ha4.7.3.5 — 2026-08-31

- corrige reconciliação de Gateway local ocorrendo antes de o Media Pool/Drive de origem terminar de remontar;
- `reconcile-agent-state.sh` agora lê `transport` e `source_path` do backend persistido e, para backends `local`, aguarda a origem virar mountpoint real antes do `/v1/gateway/switch`;
- evita falso sucesso onde `/media-union/<biblioteca>` virava apenas um bind de diretório vazio enquanto o Media Pool ainda não estava montado;
- após o switch, confirma que o stable path é mountpoint e responde a `stat` antes de declarar `Gateway ... reconciliado`;
- se a origem local não ficar pronta dentro da janela de recuperação, não aponta o stable path para pasta vazia e deixa o monitor HA tentar novamente;
- mantém sincronização automática do Agent, descoberta dinâmica de token/env em Oracle/VPS, limpeza preventiva de FUSE stale, Drive Isolation, AkiraBox/BuzzHeavier e VFS cache `off`.

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
