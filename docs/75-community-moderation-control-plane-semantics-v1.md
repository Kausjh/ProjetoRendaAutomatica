# Community Moderation Control Plane Semantics V1 - 8E9C

## Status

8E9C CONCLUIDA E VALIDADA. ETAPA 8E9 CONCLUIDA.

## Recovery

A 8E9C foi reaplicada integralmente sobre o baseline limpo `7a1a5cb`.

As tentativas anteriores revelaram tres problemas de tooling, nao de
arquitetura:

- matcher AST tratou `self._thread` como `ast.Assign`, embora fosse
  `ast.AnnAssign`;
- warning de CRLF do Git foi promovido a erro pelo PowerShell;
- `controlador.py` permaneceu false-dirty por stat cache do index mesmo
  com bytes, blob HEAD, blob index e working blob identicos.

O false-dirty foi eliminado com `git update-index --refresh`.

A reaplicacao limpa nao depende mais de anchor em `self._thread` e nao
modifica o constructor do servidor.

## Auth

A autenticacao administrativa existente continua:

`Authorization: Bearer <RADAR_ADMIN_TOKEN>`

A comparacao `hmac.compare_digest` e preservada.

Sem token configurado, Moderation falha fechado com 503.

Token ausente ou incorreto retorna 401.

O rate limiter e executado antes da autenticacao para limitar tambem
tentativas invalidas.

## Request correlation

As respostas de Moderation recebem `X-Request-Id`.

Request IDs fornecidos pelo cliente sao reutilizados somente quando
passam pela policy de tamanho e caracteres seguros.

## Rate limiting

Buckets independentes:

- read: 120 requisicoes por 60 segundos por IP;
- decision: 30 requisicoes por 60 segundos por IP.

Quando excedido:

- HTTP 429;
- `Retry-After`;
- `X-RateLimit-Limit`;
- `X-RateLimit-Remaining`.

O estado existe somente na memoria do processo.

## Audit

O ledger existente `auditoria_administrativa` e reutilizado.

Acoes:

- `moderation.admin.read.list`;
- `moderation.admin.read.detail`;
- `moderation.admin.decision`.

A auditoria registra correlacao, rota, status, codigo de erro, escopo,
IP, dispositivo e presenca de Idempotency-Key.

Ela nao registra:

- Authorization;
- `RADAR_ADMIN_TOKEN`;
- request body;
- justificativa da decision.

Falha do audit sink nao desfaz um resultado de dominio ja concluido.

## Error semantics

O corpo JSON existente e preservado.

Erros ganham o header:

`X-Moderation-Error-Code`

Mapeamento:

- 400 -> `moderation_bad_request`;
- 401 -> `moderation_unauthorized`;
- 404 -> `moderation_not_found`;
- 409 -> `moderation_conflict`;
- 429 -> `moderation_rate_limited`;
- 500 -> `moderation_internal_error`;
- 503 -> `moderation_unavailable`.

Respostas de Moderation recebem `Cache-Control: no-store`.

## Runtime

A policy e injetada no `ServidorStatusAdministrativo`.

O audit sink reutiliza o `ControladorAdministrativo` e o
`ControleAdministrativoRepository` existentes.

Isso nao habilita persistentemente Community Moderation.

## Fronteiras

A 8E9C nao:

- reinicia runtime;
- habilita Moderation persistentemente;
- habilita reconciliation automatica;
- executa canario live;
- cria User Reporting API;
- escreve Moderation live;
- escreve Trust;
- escreve Gamification.

## Validacao final

A 8E9C foi validada sobre o baseline `7a1a5cb`.

Resultados pre-closure:

- 20 testes isolados da 8E9C aprovados;
- 160 testes acumulados 8E1..8E9C aprovados;
- 209 testes Trust + Moderation aprovados;
- 95 testes de regressao do servidor administrativo aprovados;
- pre-commit aprovado;
- source audit e parse Python aprovados.

Semanticas concluidas:

- Bearer `RADAR_ADMIN_TOKEN` preservado;
- comparacao constante preservada;
- correlacao por `X-Request-Id`;
- rate limit antes da autenticacao;
- 120 reads por 60s/IP;
- 30 decisions por 60s/IP;
- HTTP 429 com `Retry-After`;
- auditoria no ledger `auditoria_administrativa`;
- Authorization, request body e justificativa nao sao auditados;
- falha de audit nao desfaz resultado de dominio;
- `X-Moderation-Error-Code`;
- `Cache-Control: no-store`;
- corpos JSON anteriores preservados.

Estado live final:

- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros de foreign key;
- nenhuma escrita live de Moderation;
- nenhuma escrita Trust.

O runtime de Community Moderation continua OFF.
A reconciliation automatica continua OFF.
Nao houve restart nem canario live.

Com 8E9A, 8E9B e 8E9C concluidas, a etapa 8E9
Moderation HTTP / Control Plane esta encerrada.

## Proximo passo

8E10A - Authenticated Report Creation.
