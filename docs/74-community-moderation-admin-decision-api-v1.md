# Community Moderation Authoritative Admin Decision API V1 - 8E9B

## Status

8E9B CONCLUIDA E VALIDADA.

## Objetivo

Expor a primeira operacao HTTP autoritativa de escrita de Community
Moderation sem contornar as fronteiras criadas nas etapas 8E3 a 8E8.

## Rota

`POST /moderation/reports/{denuncia_id}/decision`

Headers obrigatorios:

- `Authorization: Bearer <RADAR_ADMIN_TOKEN>`;
- `Idempotency-Key: <acao-idempotente>`.

JSON permitido:

- `resultado`;
- `justificativa`;
- `ocorrido_em`.

Campos como `moderator_actor_id`, `origem` e
`familia_abuso_confirmado` nao sao aceitos do cliente.

## Authority

O endpoint nao escreve diretamente no repository.

Ele chama:

`CommunityModerationService.registrar_decisao_autorizada(...)`

Esse service:

- revalida o Authorization header;
- deriva `moderator_actor_id` pela Authority;
- deriva a familia Trust a partir do motivo da denuncia;
- chama a Trust Bridge quando o resultado e `confirmed_abuse`.

## Idempotencia

`Idempotency-Key` e encaminhado como `acao_idempotencia`.

Semantica HTTP minima da 8E9B:

- 201: decisao criada;
- 200: replay idempotente exato;
- 409: colisao semantica ou conflito de estado.

A finalizacao global de error semantics pertence a 8E9C.

## Runtime

A Decision API somente recebe o
`CommunityModerationService` quando a composition root de Moderation
esta realmente ativa.

Com `COMMUNITY_MODERATION_RUNTIME_ATIVO=0`:

- a rota existe;
- o service nao e injetado;
- a escrita falha fechado com 503.

Portanto a 8E9B nao ativa persistentemente o runtime.

## Validacao

Os testes da 8E9B usam SQLite temporario.

Nenhuma decision live e criada nesta etapa.

O canario real report -> decision -> Trust permanece reservado para a
8E12.

## Fronteiras

A 8E9B nao:

- cria a User Reporting API;
- habilita runtime persistentemente;
- habilita reconciliation automatica;
- executa canario live;
- finaliza audit;
- finaliza rate limiting;
- finaliza a taxonomia completa de erros.

## Validacao final da 8E9B

A 8E9B foi validada sobre o baseline `76ea8d8`.

Resultados pre-closure:

- 14 testes isolados aprovados;
- 139 testes acumulados de Moderation aprovados;
- 188 testes Trust + Moderation aprovados;
- auditoria estrutural AST aprovada;
- pre-commit aprovado apos formatacao automatica.

A rota autoritativa concluida e:

`POST /moderation/reports/{denuncia_id}/decision`

Fronteiras HTTP validadas:

- autenticacao administrativa por `RADAR_ADMIN_TOKEN`;
- `Idempotency-Key` obrigatorio;
- cliente nao controla `moderator_actor_id`;
- cliente nao controla origem da Authority;
- cliente nao controla familia Trust;
- chamada HTTP usa `registrar_decisao_autorizada`.

Fronteiras core validadas:

- actor derivado pela Authority;
- origem derivada pela Authority;
- familia Trust derivada no `CommunityModerationService`;
- `confirmed_abuse` passa pela Trust Bridge;
- idempotencia permanece no repository/core;
- conflitos de estado permanecem no repository/core.

Fronteiras de runtime:

- Decision Service somente e injetado quando o runtime de Moderation esta ativo;
- runtime inativo falha fechado;
- runtime persistente continua OFF;
- reconciliation automatica continua OFF;
- nenhum restart ocorreu na 8E9B.

Estado live final:

- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros de foreign key;
- nenhuma escrita live da 8E9B.

O canario live continua reservado para a 8E12.

## Proximo passo

8E9C - Auth, Audit, Rate and Error Semantics.
