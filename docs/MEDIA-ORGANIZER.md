# Media Organizer / Smart Renamer

Módulo em desenvolvimento para organizar bibliotecas em Google Drive para Plex e Jellyfin sem download/reupload.

## Fluxo seguro

`Scan -> Plano -> Revisão -> Executar -> Undo`

O scan é somente leitura. Nenhum arquivo é alterado antes da confirmação do plano.

## Escopo RC1

- Tipos: Auto, Filmes, Séries e Anime.
- Perfis: Universal Plex+Jellyfin, Plex, Jellyfin e Anime/HAMA.
- Parser offline de filenames com limpeza de release tags, resolução, codec e áudio.
- Detecção SxxExx, NxE, temporada via pasta Season/Temporada e anime absoluto.
- TMDb opcional para filmes/séries/títulos de episódios.
- AniDB title catalog + Anime-Lists para anime e mapeamento AniDB -> TVDB/TMDb.
- Busca manual de correspondência para itens ambíguos.
- Score de confiança com fila de revisão.
- Rename/move via `rclone moveto` dentro do Google Drive.
- Recusa sobrescrita de destino existente.
- Legendas e sidecars com mesmo stem acompanham o vídeo.
- Manifesto das alterações e Undo em ordem inversa.
- Samples, trailers e extras conhecidos são ignorados pelo scan principal.

## Formatos

Filmes:

`Movies/Título (Ano)/Título (Ano).ext`

Séries:

`TV Shows/Série (Ano)/Season 01/Série (Ano) - S01E01 - Título.ext`

Plex pode receber `{tmdb-ID}` quando o perfil Plex estiver ativo. Jellyfin pode receber `[tmdbid-ID]` no perfil Jellyfin.

Anime/HAMA:

`Anime {anidb-ID}/Anime - 001 - Título.ext`

O perfil HAMA preserva a numeração absoluta AniDB; os mapeamentos Anime-Lists ficam disponíveis para cross-reference com TVDB/TMDb.

## Segurança

- Conta precisa estar cadastrada como leitura+escrita para Executar/Undo.
- Scan pode trabalhar sem escrita.
- Conflitos em que dois arquivos gerariam o mesmo destino são enviados para revisão.
- Arquivos de mídia não são enviados para providers; apenas nomes/títulos são usados nas pesquisas de metadados.

## Referências

- `lijunzh/plex-media-organizer`: inspiração para Scan/Plan/Execute/Undo e dry-run (MIT).
- tinyMediaManager: referência para renamer profiles, scraping, NFO e API; integração externa opcional futura.
- `DFANNN/Rename`: referência conceitual para preview + pesquisa TMDb; nenhum código copiado.
- `ZeroQI/Hama.bundle`: referência para fluxo AniDB/mapeamentos; GPLv3, nenhum código incorporado.
- `Anime-Lists/anime-lists`: dados externos de mapeamento consultados/cacheados em runtime.

## Próximos RCs

- agendamento e auto-scan;
- auto-apply somente acima de limiar configurado;
- NFO e artwork opcionais;
- regras avançadas de Specials/OVA/OP/ED;
- fingerprint PHASH/MediaInfo;
- bridge opcional da HTTP API do tinyMediaManager;
- parser `hunch` opcional;
- scan unificado de um Media Pool inteiro.
