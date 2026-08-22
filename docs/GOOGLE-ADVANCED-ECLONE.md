# Google Advanced — eclone / gclone + Service Accounts

## Finalidade

O Google Advanced Engine é destinado a cópias e operações Google Drive em que rotação de identidades e cópia server-side são úteis. Ele é separado do Media Pool usado para streaming.

Ordem automática do motor:

```text
eclone -> gclone -> Google Drive API
```

A escolha depende da configuração e da disponibilidade dos binários.

## eclone

O Manager usa como upstream:

- repositório: `ebadenes/eclone`;
- versão fixada no código desta release: `v1.73.0-mod2.0.2`.

O instalador interno baixa a release upstream para a pasta persistente de engines e registra o SHA-256 do binário instalado. O eclone não é armazenado neste repositório.

Recursos utilizados do eclone:

- rotação dinâmica de Service Accounts em erros de limite;
- Rolling SA;
- seleção inicial aleatória;
- preload de serviços;
- blacklist de Service Accounts limitadas;
- anti-thrashing entre trocas;
- reset de pacer após troca;
- detecção ampliada de limites.

## Service Accounts

Os JSONs de Service Account são dados sensíveis. Eles ficam na área persistente da instalação e **nunca devem ser versionados no GitHub**.

Cada SA precisa ter acesso real à origem e ao destino usados pela operação.

## Quando usar

Útil principalmente para:

- Google Drive -> Google Drive;
- Shared Drive -> Shared Drive;
- cópia server-side de grandes bibliotecas;
- operações automatizadas que encontram rate limits em uma única identidade.

Para upload local -> Meu Drive, OAuth normal da conta normalmente é a opção mais simples.

Para Jellyfin/Plex, o Media Pool/rclone mount é a camada principal. Rolling SA não deve ser confundido com otimização obrigatória de streaming.

## Quotas e limites

Múltiplas SAs podem distribuir limites associados à identidade usada na operação, mas **não eliminam limites pertencentes ao recurso**. Em especial, trocar a SA não transforma vários Drives em um único Drive com uma quota total infinita.

Limites do Shared Drive, do proprietário de arquivo, da organização ou outras políticas do Google continuam aplicáveis.

Os valores exatos de quota podem mudar e devem ser tratados como políticas do provedor, não como garantias do Manager.

## Armazenamento usado/livre

O Manager consulta `about.storageQuota` da Drive API e mantém cache configurável. Quando o Google fornece `usage` e `limit`, o painel mostra:

- usado;
- livre;
- total;
- percentual.

Nem todo tipo de Drive retorna um `limit` útil; nesses casos o Manager exibe o valor como indisponível em vez de estimar capacidade.

## Segurança

- pasta de Service Accounts com permissão restrita;
- validação do JSON antes de salvar;
- rejeição de arquivos grandes ou inválidos;
- binários externos instalados fora da árvore de código;
- credenciais não entram em pacotes públicos nem no GitHub.
