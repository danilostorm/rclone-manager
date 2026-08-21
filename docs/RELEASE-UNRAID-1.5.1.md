# Rclone Manager for Unraid v1.5.1

Versão estável do Rclone Manager para Unraid.

## Novidades

- novo menu **Upload** abaixo de Transferências;
- envio de arquivos e pastas do computador para os Google Drives cadastrados;
- drag & drop, múltiplos arquivos e pasta inteira;
- navegação e criação de pasta no destino;
- sessões resumíveis do Google Drive com persistência de sessão e offset;
- blocos configuráveis de 8, 16, 32 ou 64 MiB;
- até 4 uploads simultâneos;
- preservação da estrutura de subpastas;
- opções para substituir, manter os dois ou ignorar arquivos existentes;
- histórico de uploads e integração com a estimativa de cota em 24 horas;
- correção do layout 5/7 do Centro de Upload e do comportamento responsivo.

## Atualização

Extraia o pacote por cima de:

```text
/mnt/user/appdata/rclone-manager
```

Preserve:

```text
.env
data/
cache/
```

Depois execute:

```bash
cd /mnt/user/appdata/rclone-manager
chmod +x *.sh scripts/*.sh
./update.sh
```

A migração do banco é automática. Contas que recebem uploads precisam estar autorizadas com leitura/escrita. Os mounts para consumo de mídia continuam somente leitura.

O pacote de release não inclui credenciais, tokens OAuth, `rclone.conf`, banco de dados real, `.env` ou backups da instalação.
