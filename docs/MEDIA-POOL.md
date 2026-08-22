# Media Pool / Drive Union

## Objetivo

O Media Pool foi criado para reduzir a complexidade de bibliotecas grandes distribuídas em várias contas Google Drive. Em vez de cadastrar dezenas de mounts no Jellyfin/Plex, o operador escolhe somente as pastas desejadas de cada conta e o Manager entrega um único mount virtual.

## Modelo

Cada membro do Pool contém:

- conta Google (`account_slug`);
- caminho físico dentro do Drive (`source_path`);
- categoria virtual;
- prioridade;
- habilitado/desabilitado;
- permissão opcional para receber novos uploads roteados.

Exemplo:

```text
akumanimes:/Anime 1080p          -> /Animes
anime02:/Biblioteca/Animes       -> /Animes
filmes01:/Filmes 4K              -> /Filmes
filmes01:/Filmes 1080p           -> /Filmes
```

Para Jellyfin/Plex:

```text
/mnt/rclone-manager-remotes/_media-pools/stormflix/Animes
/mnt/rclone-manager-remotes/_media-pools/stormflix/Filmes
```

No Unraid o prefixo de mount pode ser diferente conforme `MOUNT_ROOT`, mas a subárvore `_media-pools/<pool>` é mantida.

## Como adicionar conteúdo

1. Crie um Media Pool.
2. Selecione uma conta Google.
3. Navegue pelas pastas dessa conta.
4. Marque somente as pastas que devem entrar no Pool.
5. Informe a categoria virtual, por exemplo `Animes`.
6. Repita para outras contas.
7. Monte o Pool.
8. Cadastre somente as categorias do mount virtual no Jellyfin/Plex.

É permitido adicionar várias pastas da mesma conta.

## Implementação

O Manager gera uma configuração rclone isolada para o Pool. Pastas que compartilham a mesma categoria são agrupadas por backend `union`; as categorias são expostas no mount principal por `combine`.

O Pool não altera o `rclone.conf` principal das contas e não move arquivos ao ser criado.

## Streaming

O Media Pool é pensado principalmente como camada de leitura para Jellyfin/Plex. A reprodução continua acessando o arquivo no Drive físico onde ele está armazenado.

Criar um Pool não soma magicamente quotas do Google. A carga pode ficar distribuída porque os arquivos permanecem em origens diferentes, mas limites associados ao arquivo, proprietário, Shared Drive ou organização continuam existindo.

## Roteamento de novos uploads

A opção **"Essas pastas podem receber upload automático"** não é necessária para streaming.

Quando habilitada, ela permite ao Manager escolher automaticamente uma origem gravável de uma categoria ao enviar um novo arquivo. A decisão pode usar:

- categoria;
- prioridade;
- espaço livre conhecido;
- disponibilidade da origem.

Exemplo:

```text
Upload -> categoria Animes
       -> Anime01: 100 GB livres
       -> Anime02: 2.8 TB livres  <- escolhido
       -> Anime03: 900 GB livres
```

Se o Pool for usado somente para Jellyfin/Plex, a opção pode permanecer desativada.

## Espaço agregado

O painel consulta a cota de cada conta e agrega `used`, `limit` e `remaining` quando a API fornece esses valores. Uma mesma conta com várias pastas no Pool é contabilizada apenas uma vez no total agregado.

Shared Drives e contas sem cota reportada podem aparecer sem total/livre conhecido. O painel não inventa capacidade quando o Google não fornece um limite confiável.

## Estado degradado

Se uma origem estiver indisponível, o Pool pode ser marcado como `degraded`. Isso não significa que os demais Drives foram perdidos; as origens saudáveis continuam independentes.

## Localizador de arquivo

O localizador pesquisa os membros físicos do Pool e informa em qual conta e caminho um arquivo existe. Isso é útil quando dezenas de Drives são apresentados como uma única biblioteca virtual.

## Exclusão

Excluir um Media Pool remove somente a configuração virtual e o mount correspondente. Não apaga arquivos nem contas Google.
