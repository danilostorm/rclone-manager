# Media Organizer RC5 — Gerenciador de Scans Persistente

RC5 adiciona controle persistente de scans ao Media Organizer.

## Estados
- queued
- scanning
- pausing
- paused
- cancelling
- cancelled
- interrupted
- planned
- error

## Recursos
- Pausar no próximo checkpoint seguro.
- Continuar do checkpoint salvo no SQLite sem perder itens já analisados.
- Cancelar preservando o plano parcial.
- Retomar scans pausados, cancelados, interrompidos ou com erro.
- Reinício do Rclone Manager converte scans ativos para `interrupted`, permitindo retomada manual.
- Persistência de `scan_cursor`, `scan_phase`, `current_path`, timestamps e heartbeat.
- Controles na lista de scans recentes e na página individual do plano.
- A página/navegador pode ser fechada; o scan continua no backend.

## Segurança
O scan permanece dry-run. Pausar/cancelar/continuar não renomeia nem move mídia. Rename/move só acontece na etapa Executar.

## Versões RC5
- VPS: 1.3.0-rc5
- Unraid: 2.0.0-rc5
- Desktop ZorinOS: 1.6.0-rc5

O Smart Classifier, NFO, títulos pt-BR e providers do RC4 permanecem incluídos.
