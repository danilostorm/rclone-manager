# Media Organizer RC3 — Multi-Source, pt-BR e NFO

Versões: VPS 1.3.0-rc3 · Unraid 2.0.0-rc3 · ZorinOS 1.6.0-rc3.

## Objetivo

Evoluir o Media Organizer para preservar a melhor identificação técnica possível para Plex/Jellyfin e, ao mesmo tempo, permitir uma biblioteca amigável em português do Brasil.

## Nomes localizados

O RC3 separa três conceitos:

- título localizado: usado por padrão nas pastas e arquivos, por exemplo `Fly, o Pequeno Guerreiro`;
- título técnico/original: preservado no plano, metadata e NFO;
- IDs externos: preservados para matching e cross-reference.

Configurações independentes permitem escolher `localized`, `technical` ou `original` para nomes de pasta e de arquivo. O idioma padrão é `pt-BR`.

## Pipeline multi-source

### Filmes e séries

- TMDb: identificação, título localizado, original title, ano, resumo, gêneros, estúdios, elenco, direção, episódios, poster/fanart e external IDs.
- NFO local existente: fonte de alta confiança e nunca sobrescrito.

### Anime

Ordem de resolução recomendada:

1. AniDB + Anime-Lists: identidade técnica, aliases, mapeamento AniDB → TVDB/TMDb e mapeamento de episódios.
2. TMDb: localização pt-BR, metadata e artwork quando existe ID mapeado.
3. AniList: títulos romaji/inglês/nativo, MAL ID e confirmação de identidade.
4. Kitsu: aliases, synopsis, episódios e confirmação secundária.
5. MAL via Jikan: fallback opcional e desativado por padrão.
6. NFO existente: se presente, recebe prioridade como metadata local conhecida.

HAMA e AMSA foram usados apenas como referência conceitual para numeração de anime e arquitetura multi-source. Ambos possuem licença GPL e nenhum código deles foi incorporado ao Rclone Manager.

O provider `Drewpeifer/plex-meta-tvdb` foi estudado como referência de integração TVDB/Plex, mas o repositório foi arquivado em abril de 2026 e o próprio autor não recomenda uso de produção. Portanto, TVDB não é dependência central do RC3; seus IDs/mapeamentos são aproveitados principalmente via Anime-Lists.

## NFO

Geração opcional, ativada por padrão:

- `movie.nfo` para filmes;
- `tvshow.nfo` para séries/animes;
- `<episódio>.nfo` para episódios.

O NFO inclui, quando disponível: título localizado, título original, ano, plot, tagline, data de estreia, rating, runtime, gêneros, estúdios, países, direção, roteiro, elenco e IDs TMDb/TVDB/IMDb/AniDB/AniList/MAL/Kitsu.

NFO já existente nunca é sobrescrito. O RC3 também lê NFO existentes — inclusive bibliotecas previamente preparadas por tinyMediaManager — como entrada para identificação.

## Artwork local

Poster e fanart locais são opcionais e desativados por padrão. Quando habilitados, o RC3 pode gerar `poster.jpg` e `fanart.jpg` a partir dos providers disponíveis, sem sobrescrever arquivos existentes.

## Anime especiais

O parser reconhece adicionalmente:

- OP / NCOP;
- ED / NCED;
- OVA / OAD;
- Special / SP;
- PV / Trailer.

No perfil HAMA, aplica faixas compatíveis conceitualmente com o modelo AniDB/HAMA. No perfil universal, itens especiais são organizados em Specials/Season 00 e casos ambíguos permanecem em revisão.

## Segurança

- Scan continua estritamente dry-run.
- Itens ambíguos nunca são autoaplicados.
- Destinos existentes não são sobrescritos.
- NFO/artwork existentes não são sobrescritos.
- Moves/renames permanecem server-side via rclone.
- NFO/artwork gerados usam `rclone rcat`; vídeos não são baixados/re-enviados.
- Toda criação de sidecar entra no manifesto.
- Undo move os arquivos de volta e remove somente sidecars criados pelo próprio plano.
- Mantém o self-heal de mounts FUSE do RC2 (`Transport endpoint is not connected`).

## Correção de parser incluída

O padrão de multi-episódio foi corrigido para não interpretar resolução como episódio final. Exemplo:

- `S01E01.1080p` → apenas episódio 1;
- `S01E01-E02` → episódios 1–2.

## Perfis

- Universal Plex + Jellyfin;
- Plex;
- Jellyfin;
- Anime / HAMA-AniDB.

Por padrão, o perfil universal usa estrutura convencional e NFO para preservar os IDs. Perfis específicos podem adicionar IDs no nome da pasta quando isso melhora o matching.
