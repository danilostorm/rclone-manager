# Atualização, verificação e rollback

## Versões estáveis atuais

- Unraid: 1.9.0
- ZorinOS Desktop: 1.5.0
- VPS/Linux: 1.2.0
- Drive Link Copier: 1.3.0

## VPS / Oracle Cloud

Instalação padrão: `/opt/rclone-manager`.

```bash
cd /opt
unzip -q rclone-manager-vps-v1.2.0.zip
cd rclone-manager-vps-v1.2.0
sudo ./install.sh
```

Verificação:

```bash
cd /opt/rclone-manager
cat VERSION
docker ps --filter name=rclone-manager-vps
docker inspect --format='{{.State.Health.Status}}' rclone-manager-vps
docker compose logs --tail=100
```

Esperado: `1.2.0` e container saudável.

O instalador preserva `.env`, `data/`, `cache/` e `backups/`.

## Unraid

```bash
cd /mnt/user/appdata/rclone-manager
# extraia o novo ZIP sobre esta pasta preservando .env, data/ e cache/
chmod +x *.sh scripts/*.sh
./update.sh
```

Antes de atualizar, recomenda-se executar:

```bash
./backup.sh ./backups
```

## ZorinOS Desktop

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.5.0_all.deb
```

Os dados persistentes do usuário são mantidos pela atualização.

## Rollback

As edições Unraid/VPS incluem `rollback.sh`. Em caso de erro, não apague `data/` nem `.env`. Consulte primeiro os logs e use o backup criado antes da atualização.

## Integridade

Toda GitHub Release inclui `SHA256SUMS.txt`. Para conferir um arquivo:

```bash
sha256sum -c SHA256SUMS.txt
```

Execute o comando no diretório que contém todos os assets listados no arquivo.
