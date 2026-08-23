# Media Renamer RC7 — Safe Rename / FileBot-style

RC7 abandona a categorização física automática e redesenha o Media Organizer como um renomeador assistido.

## Direção
- Smart Classifier removido do fluxo e da UI.
- Nunca mover automaticamente para Ação, Terror, Dublado, Dual Audio, Legendado etc.
- Padrão: `in_place` — renomear dentro da pasta atual.
- `library` continua opcional e explícito para estrutura Plex/Jellyfin, sem classificação automática.
- Preview obrigatório antes do Apply e Undo preservado.

## Correspondência estilo FileBot / Rename My TV Series
- Busca da série/anime uma única vez por job.
- TMDb para Filmes/Séries; AniDB + Anime-Lists para Anime, com TMDb quando mapeado.
- Modo `detected`: usa S/E detectados nos nomes.
- Modo `linear`: arquivos em ordem natural recebem episódios a partir de um número escolhido.
- Modo `absolute` para anime.
- Correção individual continua disponível.

## Formatos
Formato customizável com tokens:
`{title}`, `{original}`, `{year}`, `{season}`, `{season2}`, `{episode}`, `{episode2}`, `{episode3}`, `{s00e00}`, `{episode_title}`, `{ext}`.

Exemplo:
`{title} - {s00e00} - {episode_title}{ext}`

## Segurança de migração
Jobs pendentes antigos que contêm metadata `classification` são marcados `legacy_review`, têm execução bloqueada e permanecem disponíveis somente para conferência/Undo. Jobs concluídos não são removidos.

## Versões RC7
- VPS: `1.3.0-rc7`
- Unraid: `2.0.0-rc7`
- ZorinOS Desktop: `1.6.0-rc7`
