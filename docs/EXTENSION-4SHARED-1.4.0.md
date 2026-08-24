# Drive Link Copier 1.4.0 — 4shared

A extensão passa a reconhecer arquivos exibidos em pastas públicas do 4shared (`4shared.com` / `4s.io`) e páginas individuais de arquivo.

## Captura
- Em páginas de pasta, lê cada `.file-card.jsCardItem`.
- Usa `.file-card-link.jsGoFile` como URL do arquivo.
- Usa `.jsFileName` como nome preferido.
- Preserva `itemId` quando disponível.
- A URL da pasta não é enviada como se fosse um arquivo.

## Backend
O Rclone Manager VPS 1.3.0-rc9 / Drive Link API v10 reconhece `source_type=4shared` e preserva o nome capturado pela extensão.

A transferência só segue URLs que o próprio 4shared já expõe de forma pública/autorizada ao servidor. Não há bypass de login, espera, CAPTCHA, cookies de sessão ou recursos Premium.

## Validação
O HTML de teste usado continha 20 cards de arquivo. Os 20 links individuais `4s.io/video/...` foram reconhecidos pela função `parseSupportedUrl` como `source=4shared`, com 20 IDs únicos.
