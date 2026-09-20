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

## Validacao operacional real

Concluida em 20/09/2026.

O Public App foi validado em um Samsung SM-M526B real usando o development
client existente e o backend real.

Este smoke no dispositivo Android real confirmou a superficie de
gamificacao de ponta a ponta.

A tela Perfil exibiu corretamente:

- nivel 2;
- 140 XP;
- 40/150 XP no nivel;
- 110 XP restantes;
- 27% de progresso;
- reputacao 0;
- 3 badges;
- 3 de 6 conquistas desbloqueadas.

O UI dump confirmou os textos principais da superficie.

Durante a primeira tentativa, ainda na Home, o development client exibiu um
warning de React sobre state update antes do mount. O warning nao reapareceu
no reteste da tela Perfil e nao foi atribuido a gamificacao.

A observacao permanece separada e nao invalida o gate da Etapa 6.

Gamification & Reputation V1 esta concluida de ponta a ponta.
