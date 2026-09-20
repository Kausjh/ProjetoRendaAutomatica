# Gamification & Reputation V1 - Public App Surface

## Etapa 6E

A 6E conecta o Public App ao endpoint autenticado:

`GET /api/v1/me/gamification`

A superficie fica dentro da tela Conta.

Nao e criada uma nova entrada na bottom navigation e nao e criada uma
rota dedicada nesta etapa.

## Arquitetura

O modulo `src/gamification` separa:

- tipos;
- presenter;
- query React Query;
- componente visual.

O `public-api-client` conhece a rota HTTP.

O componente visual nao conhece tokens, conta_id, SQLite ou regras de XP.

## Fonte de verdade

O app apenas apresenta os valores retornados pelo backend.

Ele nao recalcula XP, nivel, reputacao, progresso, conquistas ou badges.

A unica transformacao visual do percentual e limitar a largura da barra ao
intervalo de zero a cem para impedir overflow visual.

## Superficie

A tela Conta passa a mostrar:

- nivel atual;
- XP total;
- progresso no nivel;
- XP faltante;
- reputacao;
- quantidade de badges;
- conquistas;
- progresso individual;
- refresh manual.

## Fronteiras

A 6E nao permite escrita de gamificacao.

Ela nao implementa missoes, reputacao comunitaria, trust, historico de
eventos, alteracao do scoring de ofertas ou Price Intelligence.

## Proximo passo

Depois do commit da 6E sera executado smoke no dispositivo Android real e,
se aprovado, a Etapa 6 sera encerrada formalmente.
