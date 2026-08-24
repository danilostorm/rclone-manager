# RC10 Native 4shared + Settings Tabs

## Escopo

O RC10 substitui o suporte experimental de página do 4shared do RC9 por uma integração nativa no Rclone Manager e reorganiza a tela Configurações em abas.

## 4shared nativo

- REST API oficial `v1_2`.
- OAuth 1.0: Request Token → autorização no 4shared → Access Token.
- Endpoints usados: `/oauth/initiate`, `/oauth/authorize`, `/oauth/token`, `/user`, `/files/{id}` e `/files/{id}/download`.
- O Manager não armazena a senha 4shared; guarda apenas Consumer Key/Secret e tokens OAuth no armazenamento privado de configurações.
- A extensão entrega o ID público do arquivo. Não envia cookies/sessão do navegador.
- Download por `/files/{id}/download`, com `Range` para retomada quando houver arquivo parcial.
- Pipeline continua sendo download temporário → upload Google confirmado → limpeza.
- Falha de autenticação/permissão do 4shared vira `waiting_retry` e pode ser repetida depois de corrigir a integração.
- Não implementa bypass de CAPTCHA, espera, Premium, DRM ou restrições do provedor.
- Drive Link API passa de `v10` para `v11`.

## Configurações em abas

A tela agora tem:

1. Google
2. Integrações
3. Mídia
4. Transferências
5. Notificações
6. Segurança

Todos os campos existentes no RC9 foram preservados. A aba Integrações recebe o novo card 4shared com Consumer Key, Consumer Secret, callback, conectar/reconectar, testar e desconectar.

As abas usam hash na URL (por exemplo `#settings-integrations`) e rolagem horizontal no mobile, preservando o layout desktop.

## Extensão 1.5.0

A captura 4shared continua baseada apenas nos links/IDs públicos presentes no DOM. A 1.5.0 passa a exibir o estado `4shared nativo: conectado/não conectado` retornado pelo RC10 e orienta o usuário para Configurações → Integrações quando necessário.

## Testes locais

- `py_compile` nos módulos alterados.
- parsing dos 24 templates Jinja.
- sintaxe JavaScript da extensão via `node --check`.
- assinatura OAuth HMAC-SHA1 comparada com `oauthlib` usando nonce/timestamp fixos.
- teste mock do download oficial com `Range: bytes=123-`.
- extração do ID `XXd34ZcNee` da URL `4s.io/video/...`.
- comparação dos campos da tela Configurações: nenhum dos 51 campos do RC9 foi removido; 2 campos 4shared foram adicionados.
- integridade ZIP/TAR e verificação de ausência de banco/cache/credenciais nos pacotes.

## Limitação de validação

O ambiente local de empacotamento não possui Flask instalado, portanto não houve boot completo da aplicação web nesse ambiente. O fluxo OAuth/download real também depende de Consumer Key/Secret e de uma conta 4shared autorizada, então deve ser validado no Oracle depois da instalação.
