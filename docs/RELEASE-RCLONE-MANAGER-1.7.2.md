# Rclone Manager v1.7.2 — Release unificada

Esta release reúne **todos os downloads atuais em um único lugar**.

## Versões incluídas

- **Unraid 1.7.2** — `rclone-manager-unraid-v1.7.2.zip`
- **ZorinOS Desktop 1.3.2** — ZIP e pacote `.deb`
- **Linux / VPS 1.0.3** — ZIP e TAR.GZ, instalação padrão em `/opt/rclone-manager`
- **Drive Link Copier 1.0.1** — extensão para Chrome/Chromium
- **SHA256SUMS.txt** — checksums de todos os downloads

## Drive Link Copier

A extensão detecta links Google Drive presentes na página, permite selecionar vários itens, escolher uma das contas Google cadastradas no Rclone Manager, escolher a pasta de destino e opcionalmente criar uma nova pasta para agrupar todo o conteúdo.

A cópia Google Drive → Google Drive usa a API oficial do Google Drive (`files.copy`). O Manager só marca um item como concluído depois de receber o novo `fileId` e confirmar que o arquivo copiado pertence à pasta de destino selecionada.

Nesse fluxo o conteúdo do arquivo não precisa ser baixado para o disco da VPS: a cópia é realizada no lado do Google.

## Correção importante

Corrige o comportamento da versão inicial da integração que podia indicar uma cópia como concluída apenas pelo retorno do comando, sem validar a presença real do arquivo no destino.

## Atualização VPS

Extraia o ZIP em uma pasta temporária e execute o instalador como root/sudo. A instalação permanece em `/opt/rclone-manager` e preserva `.env`, `data/`, `cache/` e `backups/`.

```bash
cd /tmp
rm -rf rclone-vps-103
mkdir rclone-vps-103
cd rclone-vps-103
unzip /caminho/rclone-manager-vps-v1.0.3.zip
sudo ./install.sh
```

## Atualização Unraid

Preserve `.env`, `data/` e `cache/`, extraia a atualização por cima de `/mnt/user/appdata/rclone-manager` e execute:

```bash
cd /mnt/user/appdata/rclone-manager
chmod +x *.sh scripts/*.sh
./update.sh
```

## Atualização ZorinOS

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.3.2_all.deb
```

Os dados persistentes são preservados durante a atualização.

## Instalação da extensão

Extraia `rclone-manager-drive-link-copier-v1.0.1.zip`, abra `chrome://extensions`, habilite **Modo do desenvolvedor** e use **Carregar sem compactação**. Nas opções, informe a URL HTTPS do Rclone Manager e a API Key gerada em **Configurações**.

## Segurança

Os pacotes públicos não incluem `.env`, `rclone.conf`, banco da instalação, tokens OAuth, Client Secrets, chaves privadas ou backups reais. A API Key da extensão deve ser tratada como credencial e não deve ser publicada.
