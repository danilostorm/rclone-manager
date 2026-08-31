# Changelog

## 1.4.0-rc11-ha4.7.3.1 — 2026-08-31

- corrige o SHA-256 do payload usado por `git-install.sh` / `git-update.sh`;
- deploy via Git passa a aplicar um overlay idempotente sobre o payload atual antes do build;
- adiciona reconhecimento de AkiraBox (`akirabox.to`, `akirabox.com`) e BuzzHeavier (`buzzheavier.com`, `bzzhr.co`, `bzzhr.to`);
- adiciona resolução dos links externos antes do estágio download → upload;
- preserva `size_bytes`, `size_text` e extensão enviados pela extensão do navegador;
- Gerenciador de tarefas passa a expor tamanho total/conhecido e extensões quando disponíveis;
- se o manifesto SHA estiver desatualizado mas o payload estiver limpo e rastreado pelo Git, o instalador avisa e continua; alterações locais no payload continuam bloqueando a instalação.

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
