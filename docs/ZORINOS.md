# Rclone Manager Desktop no ZorinOS

Versão estável atual: **1.1.2**.

## Instalação / atualização

Baixe o pacote `.deb` da release `zorinos-v1.1.2` e rode:

```bash
sudo apt update
sudo apt install ./rclone-manager-desktop-zorinos_1.1.2_all.deb
```

Depois procure **Rclone Manager** no menu do ZorinOS.

Atualizações futuras usam o mesmo comando com o novo `.deb`; não é necessário remover a versão anterior.

## Centro de Upload

O menu **Upload** permite:

- enviar arquivos individuais, vários arquivos ou uma pasta inteira;
- arrastar e soltar arquivos;
- escolher Drive e pasta de destino;
- criar pasta no destino;
- preservar subpastas;
- escolher entre substituir, renomear ou ignorar arquivos existentes;
- usar sessões resumíveis do Google Drive para tentar continuar uploads interrompidos;
- acompanhar taxa instantânea, taxa média, progresso e histórico;
- continuar o upload durante a navegação normal entre os menus do aplicativo.

Contas de destino precisam estar autorizadas com **leitura/escrita**. Isso não torna os mounts graváveis: os mounts continuam read-only.

## Speedtest

A partir da v1.1.2 existe o menu **Speedtest** com:

- ping;
- jitter;
- download;
- upload;
- perfis Rápido, Padrão e Completo;
- histórico persistente dos testes.

Na edição Desktop o teste mede a conexão do próprio computador ZorinOS.

## Dados locais

O pacote do aplicativo e os dados do usuário ficam separados. Atualizar o `.deb` não deve apagar os dados persistentes.

Diretórios usados pela edição Desktop:

```text
~/.local/share/rclone-manager-desktop/
~/.cache/rclone-manager-desktop/
~/RcloneDrives/
```

## Google OAuth

Use um projeto próprio no Google Cloud com **Google Drive API** ativada. Não compartilhe Client Secret nem tokens.

Para Desktop, o callback local usado pelo aplicativo é:

```text
http://127.0.0.1:8787/oauth/google/callback
```

## Backup antes de atualizar

O `.deb` preserva os dados do usuário, mas um backup pelo próprio Rclone Manager continua recomendado antes de mudanças maiores.

## Desinstalação

```bash
sudo apt remove rclone-manager-desktop
```

Faça backup antes de qualquer limpeza manual dos diretórios de dados.
