# Media Organizer RC4 — Smart Classifier

RC4 adiciona classificação automática segura ao Media Organizer, ainda dentro do fluxo `Scan -> Plano -> Revisão -> Executar -> Undo`.

## Filmes e Séries

- Usa gêneros e keywords do TMDb.
- Escolhe uma categoria física principal em português: Ação, Aventura, Animação, Comédia, Crime, Drama, Terror, Ficção Científica, Mistério, Suspense, Romance, Documentário, Família, Fantasia, História, Guerra, Música, Faroeste etc.
- Regra especial `Luta` para keywords como martial arts, kung fu, karate, boxing, MMA, wrestling, fighter/tournament e equivalentes.
- Todos os gêneros continuam preservados no NFO; somente a categoria principal define a pasta física.

Estrutura exemplo:

`Filmes/Luta/Título (Ano)/Título (Ano).mkv`

`Séries/Drama/Série/Season 01/Série - S01E01.mkv`

## Anime

Quando habilitado, o Manager usa `ffprobe` no mount para inspecionar uma mídia representativa por pasta e detectar as faixas reais de áudio/legenda:

- Português + outro áudio -> `Dual Audio`
- Somente áudio português -> `Dublados`
- Sem áudio português + legenda pt-BR -> `Legendados`
- Faixas detectadas sem pt-BR -> `Sem PT-BR`

Se ffprobe/mount estiver indisponível, usa nome e caminho como fallback para palavras como `Dual Audio`, `Dublado`, `Legendado`, `pt-BR` etc.

Subcategorias opcionais:

- `Filmes de Anime`
- `OVA e OAD`
- `Especiais`

Exemplos:

`Animes/Dual Audio/Fly, o Pequeno Guerreiro/Season 01/...`

`Animes/Legendados/OVA e OAD/Título/...`

## Evitar pastas duplicadas

Se a pasta destino já termina em `Animes`, `Filmes`, `Séries` ou na própria categoria, o prefixo repetido é removido automaticamente. Exemplo: destino `Animes` + classificação `Animes/Dual Audio` gera `Animes/Dual Audio`, não `Animes/Animes/Dual Audio`.

## Segurança

- Classificação faz parte somente do plano até o usuário executar.
- O caminho proposto e a categoria aparecem na prévia.
- Rename/move continua server-side via rclone.
- NFO recebe tags de classificação e preserva os gêneros completos.
- Toda alteração continua registrada no manifesto para Undo.
- `ffmpeg/ffprobe` passa a fazer parte das dependências VPS, Unraid e Desktop.

## Versões RC4

- VPS: `1.3.0-rc4`
- Unraid: `2.0.0-rc4`
- ZorinOS Desktop: `1.6.0-rc4`
