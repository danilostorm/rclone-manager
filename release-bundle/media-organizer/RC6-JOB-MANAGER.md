# Media Organizer RC6 — Gerenciador de Jobs Persistente

RC6 amplia o RC5 para controlar também a fase real de execução (rename/move), e não apenas o scan.

## Estados de execução
- `apply_queued`
- `applying`
- `apply_pausing`
- `apply_paused`
- `apply_cancelling`
- `apply_cancelled`
- `apply_interrupted`
- `apply_error`
- `completed` / `completed_with_errors`

## Checkpoint persistente
A seleção e a ordem ficam persistidas em `media_organizer_items.apply_selected/apply_order`. O job guarda `apply_cursor`, `apply_total`, fase, caminho atual, heartbeat e timestamps.

Pausa e cancelamento são honrados entre itens completos para evitar parar no meio de um conjunto vídeo + companions + sidecars.

## Reinício e retomada
Jobs ativos de Apply viram `apply_interrupted`. Ao continuar, o Manager usa o cursor salvo e o manifesto de ações para reconhecer moves já concluídos no Drive sem repeti-los.

O manifesto cria ações em estado `pending` antes da operação e `applied` depois. O Undo reconcilia ações pendentes em caso de queda no pequeno intervalo entre o move e a gravação final do status.

## UI
`Scans recentes` vira `Jobs / Operações recentes`, com controles distintos para Scan e Execução na lista e na página do plano.

## Segurança do upgrade RC5 -> RC6
O patch VPS bloqueia o restart caso detecte um job RC5 em `applying` ou `undoing`, pois o RC5 ainda não possui checkpoint persistente da fase Apply. Deve-se aguardar essa operação terminar; após instalar RC6, Apply passa a ser retomável.

## Testes executados
- Migração RC5 -> RC6 e recuperação de `scanning` / `applying`.
- Pausa de Apply em 1/3 e retomada até 3/3 sem repetir move.
- Cancelamento em 1/3 e continuação até 3/3.
- Recuperação idempotente quando o destino já existe após uma queda.
- Undo retorna itens aplicados para `planned`.
- Templates Jinja, sintaxe Python e integridade ZIP/TAR/DEB.

## Versões
- VPS `1.3.0-rc6`
- Unraid `2.0.0-rc6`
- ZorinOS Desktop `1.6.0-rc6`
