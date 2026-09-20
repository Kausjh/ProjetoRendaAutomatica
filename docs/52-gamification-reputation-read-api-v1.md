# Gamification & Reputation V1 - Read API

## Etapa 6D

A 6D expoe uma leitura autenticada do estado de progressao do usuario.

Rota:

`GET /api/v1/me/gamification`

A identidade vem exclusivamente de `X-User-Session`.

O cliente nao envia `conta_id`.

## Resposta

A resposta contem:

- XP total;
- nivel atual;
- reputacao atual;
- quantidade de eventos;
- progresso para o proximo nivel;
- conquistas;
- badges desbloqueadas;
- versao do ruleset.

## Fonte de verdade

XP, reputacao e quantidade de eventos continuam vindo do core de
gamificacao.

Os thresholds de nivel continuam pertencendo ao ruleset versionado.

Conquistas e badges continuam sendo avaliadas pela politica definida
em `services/gamification_achievements.py`.

O controller HTTP apenas serializa a leitura produzida pelo
`GamificationReadService`.

## Progresso de nivel

Para um nivel nao-maximo sao expostos:

- XP de inicio do nivel;
- XP do proximo nivel;
- XP acumulado dentro do nivel;
- XP necessario dentro do nivel;
- XP faltante;
- percentual de progresso.

No nivel maximo:

- `xp_proximo_nivel` e `null`;
- `xp_necessario_no_nivel` e `null`;
- `xp_faltante` e zero;
- `percentual` e 100;
- `nivel_maximo` e `true`.

## Runtime

O `GamificationService` criado pela ativacao da 6C e reutilizado.

Nao existe um segundo ledger, ruleset ou mecanismo de pontuacao.

Se a gamificacao estiver inativa, a rota responde 503 em vez de
inventar dados.

## Fronteiras

A 6D e somente leitura.

Ela nao:

- concede XP;
- concede reputacao;
- cria eventos;
- altera watchlist;
- cria missoes;
- pontua Community Discovery;
- influencia score de ofertas;
- altera Price Intelligence;
- modifica o Public App.

A integracao visual fica para a proxima subetapa.
