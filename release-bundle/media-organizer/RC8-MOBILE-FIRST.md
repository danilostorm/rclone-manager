# RC8 — Mobile First UI

A RC8 redesenha a WebUI para uso real em celular, preservando o layout desktop acima de 820px.

## Navegação móvel
- topbar sticky com botão de menu e atalho para adicionar Drive;
- sidebar desktop vira drawer com backdrop;
- bottom navigation fixa com Início, Transferir, Renomear, Pool e Mais;
- soft-navigation também marca a rota ativa na bottom bar;
- suporte a safe-area/notch/home indicator.

## Componentes responsivos
- tabelas são convertidas em cards no mobile; os labels são derivados automaticamente dos cabeçalhos;
- formulários ficam em uma coluna;
- inputs usam 16px no mobile para evitar zoom automático no iOS;
- botões e controles recebem alvos touch maiores;
- paths quebram linha sem causar scroll horizontal;
- grids, cards, badges, progressos e ações são reorganizados para telas estreitas.

## Telas priorizadas
- Dashboard;
- Transferências;
- Media Renamer / Jobs;
- Media Pool;
- Upload;
- OneDrive Import;
- Speedtest e Sistema.

## Drive Browser
- toolbar reorganizada em linhas;
- busca com input em largura total;
- rows compactas em duas colunas;
- meta e ações passam para linhas inferiores quando necessário;
- sem scroll horizontal obrigatório.

## Ações sticky no mobile
- iniciar transferência;
- iniciar/pausar upload;
- criar prévia do Media Renamer;
- executar renomes selecionados.

## Segurança
RC8 é uma alteração de interface. Não muda banco, remotes, Media Pools, regras de transferência nem a lógica do Safe Renamer. O patch VPS cria backup dos arquivos substituídos e bloqueia restart se existir Apply/Undo ativo.

## Versões
- VPS: `1.3.0-rc8`
- Unraid: `2.0.0-rc8`
- Desktop ZorinOS: `1.6.0-rc8`
