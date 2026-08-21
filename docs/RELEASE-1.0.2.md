# Rclone Manager Desktop for ZorinOS v1.0.2

Versão estável recomendada para ZorinOS/Ubuntu.

## Correções

- corrige a inicialização do aplicativo desktop: o launcher agora verifica corretamente `/api/health`;
- melhora o diagnóstico quando a porta local não inicia ou está ocupada;
- corrige os campos de seleção claros no WebKitGTK/ZorinOS;
- aplica tema escuro consistente aos dropdowns, opções e estados desabilitados;
- alinha os metadados internos e a identificação da versão em `1.0.2`.

## Atualização

A atualização preserva os dados persistentes do usuário. Instale o novo pacote por cima da versão anterior:

```bash
sudo apt install ./rclone-manager-desktop-zorinos_1.0.2_all.deb
```

## Segurança

Os pacotes oficiais não incluem `.env`, `rclone.conf`, bancos da instalação, tokens OAuth, Client Secret, senhas, webhooks ou outros dados persistentes do usuário.
