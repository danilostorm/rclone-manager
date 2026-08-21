# Rclone Manager Desktop for ZorinOS v1.1.1

Versão estável do Rclone Manager Desktop para ZorinOS/Ubuntu.

## Novidades

- novo menu **Upload** abaixo de Transferências;
- upload de arquivos, múltiplos arquivos e pasta inteira;
- drag & drop;
- navegador de pasta de destino e criação de pasta;
- preservação da estrutura de subpastas;
- sessões resumíveis do Google Drive com tentativa de retomada;
- blocos configuráveis de 8, 16, 32 ou 64 MiB;
- até 4 uploads simultâneos;
- opções para substituir, manter os dois ou ignorar arquivos existentes;
- histórico e integração com a estimativa de cota nas últimas 24 horas;
- correção do layout das colunas do Centro de Upload no WebKitGTK/ZorinOS.

## Instalação / atualização

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.1.1_all.deb
```

A atualização preserva os dados locais do usuário em `~/.local/share/rclone-manager-desktop/`.

Contas usadas como destino de upload precisam estar autorizadas com leitura/escrita. Os mounts continuam somente leitura.

Os pacotes publicados não incluem `.env`, `rclone.conf`, banco de dados, tokens OAuth, Client Secret, chaves privadas ou outros dados persistentes da instalação.
