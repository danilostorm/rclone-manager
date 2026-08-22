# Changelog

## Release unificada 1.7.2 — Unraid 1.7.2 / ZorinOS 1.3.2 / VPS 1.0.3 / Extensão 1.0.1

- reúne **Unraid, ZorinOS, VPS e Drive Link Copier em uma única GitHub Release**;
- adiciona a extensão Chrome/Chromium **Drive Link Copier 1.0.1**, que detecta múltiplos links Google Drive em páginas;
- permite selecionar a conta e a pasta de destino no Rclone Manager e criar uma pasta nova para agrupar vários links;
- substitui a confirmação baseada somente no retorno do comando por cópia via Google Drive API `files.copy`;
- só marca sucesso depois de receber o novo `fileId` e confirmar a pasta `parent` de destino;
- corrige o falso positivo em que a interface podia indicar arquivos copiados mesmo sem aparecerem no Drive de destino;
- no fluxo Google Drive → Google Drive, o conteúdo não precisa ser armazenado no disco local da VPS;
- mantém Backup Completo Portátil v2, OneDrive compartilhado, upload, transferências e Speedtest;
- desativa a publicação automática de releases separadas por edição; novas versões passam pelo workflow unificado.

## Unraid 1.7.0

- adiciona **Backup Completo Portátil v2** com banco, Google Drive, rclone, credenciais OAuth/tokens e Microsoft/OneDrive;
- adiciona restauração/migração das configurações completas;
- preserva correções de **Compartilhados comigo** e fallback Microsoft Graph `/content`;
- mantém processamento OneDrive arquivo por arquivo e limpeza após upload confirmado.

## ZorinOS Desktop 1.3.0

- adiciona **Backup Completo Portátil v2** compatível com Unraid e VPS;
- inclui Google Drive, rclone, credenciais OAuth/tokens, Microsoft/OneDrive, banco, histórico e configurações;
- mantém importação OneDrive compartilhada e retomada validadas.

## VPS 1.0.1

- edição Linux/VPS para instalação em `/opt/rclone-manager`;
- compatível com restauração do Backup Completo Portátil v2;
- inclui importação OneDrive → Google Drive com as correções validadas;
- preparada para execução persistente em servidor e Oracle Cloud/Ubuntu.

## Unraid 1.6.9

- corrige HTTP 400 por CSRF na análise/importação OneDrive;
- mantém a navegação e análise de **Compartilhados comigo**;
- adiciona fallback pelo endpoint Microsoft Graph `/drives/{drive-id}/items/{item-id}/content` quando a Microsoft não retorna `@microsoft.graph.downloadUrl`;
- segue o redirect `Location` da Microsoft e preserva downloads retomáveis por `Range` na URL temporária real;
- melhora o fluxo OneDrive → Google Drive sem apagar o temporário antes da confirmação do upload no Google.

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
