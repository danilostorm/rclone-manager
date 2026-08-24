# RC12 Roadmap — MultiServer Replica Engine

Follow-up do RC11 MultiServer Foundation.

## Objetivo

Transformar o estado de réplica manual do RC11 em replicação verificada e segura, suficiente para permitir failover automático sem assumir que dois servidores possuem os mesmos arquivos.

## Requisitos

1. Manifesto incremental por biblioteca: path, tamanho, mtime, hash seletivo e generation.
2. Coverage calculado automaticamente; nenhum operador precisa marcar 100% manualmente.
3. Fila persistente de cópia/replicação com pausa, retomada e cancelamento.
4. Replicação preferencialmente direta entre storages pela Tailscale, sem fazer o Controller carregar os bytes.
5. Delete com tombstone/quarentena; nunca apagar imediatamente todas as réplicas.
6. Verificação pós-cópia antes de promover réplica para READY.
7. Re-sync e reconciliação depois de failover/failback.
8. Bandwidth limit e janela de replicação por biblioteca/nó.
9. Histórico e alertas de divergência.
10. Split-brain protection: uma única autoridade de escrita por biblioteca.

## Critério para failover automático

Uma réplica só poderá ser promovida automaticamente quando o Replica Engine tiver emitido uma geração verificada e `coverage=100%` para a biblioteca.
