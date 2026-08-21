# Changelog

## ZorinOS Desktop 1.1.2

- mantém o Centro de Upload introduzido na 1.1.1;
- corrige uploads que eram interrompidos ao navegar para outro menu do Rclone Manager;
- upload passa a continuar ativo durante a navegação interna normal entre Dashboard, Transferências, Upload, Speedtest, Configurações e Sistema;
- adiciona taxa instantânea e taxa média de upload na fila e no histórico;
- adiciona progresso geral com velocidade agregada para uploads simultâneos;
- novo menu **Speedtest** abaixo de Upload;
- Speedtest mede ping, jitter, download e upload, com perfis Rápido, Padrão e Completo;
- histórico de Speedtests persistido no banco;
- mantém retomada por sessão resumível do Google Drive quando o aplicativo/conexão realmente é interrompido;
- versão validada em uso real no ZorinOS e promovida a Stable.

## Unraid 1.5.2

- mantém o Centro de Upload da 1.5.1;
- upload continua ativo durante navegação entre as páginas do Manager;
- adiciona taxa instantânea e média de transferência na fila e no histórico;
- adiciona velocidade agregada da fila de uploads simultâneos;
- novo menu **Speedtest** com ping, jitter, download e upload;
- perfis Rápido, Padrão e Completo, com histórico persistente;
- o Speedtest mede a conexão do próprio servidor Unraid;
- preserva upload em blocos, sessões resumíveis e estimativa de cota;
- versão promovida a Stable após validação funcional do fluxo compartilhado com a edição Desktop.

## ZorinOS Desktop 1.1.1

- novo **Centro de Upload** para enviar arquivos e pastas do computador diretamente aos Google Drives cadastrados;
- drag & drop, múltiplos arquivos e seleção de pasta inteira;
- escolha visual do Drive e da pasta de destino, busca e criação de pastas;
- uploads em blocos de 8/16/32/64 MiB e até 4 uploads simultâneos;
- sessões resumíveis do Google Drive, com persistência de sessão/offset para tentativa de retomada ao selecionar novamente o mesmo arquivo;
- opções de conflito: substituir, manter os dois ou ignorar;
- histórico de uploads e integração com a estimativa de cota das últimas 24 horas;
- corrige o layout das colunas 5/7 do Centro de Upload no WebKitGTK/ZorinOS e melhora o comportamento responsivo;
- mantém as correções anteriores do launcher local (`/api/health`) e do tema escuro dos selects.

## Unraid 1.5.1

- novo **Centro de Upload** acessível pelo navegador;
- upload direto do computador para qualquer conta Google Drive autorizada com escrita;
- upload em blocos usando sessões resumíveis do Google Drive, sem exigir uma cópia completa permanente do arquivo no armazenamento do Manager;
- múltiplos arquivos, pasta inteira, drag & drop, preservação de subpastas e criação de pastas no destino;
- até 4 uploads simultâneos e blocos configuráveis de 8/16/32/64 MiB;
- tratamento de conflitos: substituir, renomear o novo ou ignorar;
- nova tabela `upload_jobs` para histórico, sessão e offset de retomada;
- integração com estimativa de cota de transferência nas últimas 24 horas;
- corrige o layout das colunas 5/7 do Centro de Upload e o comportamento responsivo;
- mounts continuam somente leitura; escrita ocorre apenas pelas operações autorizadas do Manager.

## ZorinOS Desktop 1.0.2

- corrige a inicialização do launcher local usando `/api/health`;
- melhora a mensagem de erro quando o servidor local não inicia;
- corrige dropdowns/selects claros no WebKitGTK do ZorinOS;
- aplica tema escuro consistente aos campos de seleção;
- alinha os metadados e identificação interna da versão;
- pacote de release sem dados persistentes da instalação.

## ZorinOS Desktop 1.0.0

- primeira edição desktop para ZorinOS/Ubuntu;
- execução local sem Docker;
- interface GTK/WebKit;
- mounts em `~/RcloneDrives/`;
- múltiplos Google Drives e transferências;
- compatibilidade com backup da edição Unraid.

## Unraid 1.4.0 Final

- backup/restore pela WebUI;
- diagnóstico completo;
- notificações Telegram/Discord;
- retry com backoff;
- checkpoint com verificação de destino;
- logs exportáveis;
- estimativa de uso em 24h;
- update com backup e rollback.
