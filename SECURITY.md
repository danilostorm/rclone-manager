# Segurança

Nunca publique neste repositório:

- `.env` real;
- Google Client Secret;
- access/refresh tokens OAuth;
- `rclone.conf` de contas reais;
- bancos SQLite da instalação;
- backups gerados pela WebUI;
- senhas administrativas;
- tokens Telegram ou webhooks Discord;
- chaves privadas.

Os pacotes publicados aqui foram preparados sem os dados persistentes de uma instalação real.

Antes de qualquer release futura, revise os arquivos e procure por credenciais reais. Se um segredo for publicado por engano, revogue/rotacione o segredo imediatamente no provedor correspondente.