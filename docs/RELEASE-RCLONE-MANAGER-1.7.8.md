# Rclone Manager v1.7.8 — release unificada

**Status: Stable.**

Release estável contendo todas as edições atuais do projeto na mesma página de download.

## Versões incluídas

- **Unraid 1.7.8**
- **ZorinOS Desktop 1.3.8**
- **Linux / VPS 1.0.9**
- **Drive Link Copier 1.2.3** para Chrome/Chromium

## Destaques desde a release unificada 1.7.2

- Drive Link API evoluída para **v8**;
- extensão detecta Google Drive, OneDrive/SharePoint, MediaFire, Dropbox, Pixeldrain e links HTTP/HTTPS diretos suportados;
- Google Drive → Google Drive usa `files.copy` server-side e valida o novo `fileId`/destino antes de concluir;
- fontes externas usam o fluxo econômico de disco: **download de um arquivo → upload resumível → confirmação → limpeza → próximo arquivo**;
- gerenciador **API / Extensão** com status, destino, progresso, tráfego, temporário, pausa, retomada, cancelamento e exclusão;
- **fila persistente FIFO**, prioridade por “Iniciar agora”, reordenação e execução serial;
- **Tentar novamente** e retorno ao fim da fila para tarefas com erro corrigível;
- criação e exclusão de pastas Google Drive diretamente pela extensão;
- ao trocar a conta de destino, a extensão carrega as pastas automaticamente;
- destino precisa ser explicitamente confirmado antes de iniciar a importação;
- removida a opção redundante “Criar uma pasta para agrupar o conteúdo selecionado” da extensão;
- mensagens de erro de permissão/link indisponível mais claras;
- preservação de `.env`, `data/`, `cache/` e `backups/` nas atualizações da VPS;
- metadados Docker/installer da VPS alinhados para **1.0.9**.

## Arquivos desta release

- `rclone-manager-unraid-v1.7.8.zip`
- `rclone-manager-desktop-zorinos-v1.3.8.zip`
- `rclone-manager-desktop-zorinos_1.3.8_all.deb`
- `rclone-manager-vps-v1.0.9.zip`
- `rclone-manager-vps-v1.0.9.tar.gz`
- `rclone-manager-drive-link-copier-v1.2.3.zip`
- `SHA256SUMS.txt`

## Atualização VPS

```bash
cd /tmp
rm -rf rclone-vps-109
mkdir -p rclone-vps-109
cd rclone-vps-109
unzip /opt/rclone-manager-vps-v1.0.9.zip
cd rclone-manager-vps-v1.0.9
chmod +x install.sh update.sh rollback.sh backup.sh uninstall.sh
chmod +x scripts/*.sh
sudo ./install.sh
```

O instalador preserva os dados persistentes da instalação existente.

## Segurança

Os pacotes públicos não incluem `.env`, `rclone.conf`, banco SQLite, tokens OAuth, Client Secrets, API Keys ou backups reais. O backup portátil completo continua sendo material sensível e não deve ser publicado ou compartilhado.
