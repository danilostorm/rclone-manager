# Segurança

Nunca publique neste repositório ou em uma GitHub Release:

- `.env` real;
- Google Client Secret;
- access/refresh tokens OAuth;
- `rclone.conf` de contas reais;
- JSONs de **Google Service Accounts**;
- bancos SQLite da instalação;
- backups gerados pela WebUI;
- senhas administrativas;
- API Keys;
- tokens Telegram ou webhooks Discord;
- arquivos `.pem`, `.key` ou qualquer chave privada;
- cache e temporários contendo dados do usuário.

## Código de release

A cadeia reproduzível usa somente bases históricas versionadas e patches de código em `release-bundle/source-full/`. O workflow de publicação verifica nomes de arquivos sensíveis antes de empacotar os artefatos.

## eclone / gclone

Binários externos como eclone/gclone não são versionados junto com credenciais. O eclone é instalado a partir do upstream configurado e fica na área persistente de engines da instalação.

## Service Accounts

Os JSONs de Service Account devem permanecer somente na instalação do operador, com permissões restritas. Nunca os adicione à cadeia de release, aos pacotes públicos ou a commits.

## Incidente de segredo

Se uma credencial for publicada por engano, removê-la do Git **não é suficiente**. Revogue/rotacione imediatamente a credencial no Google/Microsoft/provedor correspondente e depois limpe o histórico quando necessário.
