# Community Trust Evidence History API V1 - 8F3

## Status

8F3 CONCLUIDA E VALIDADA.

## Objetivo

A 8F3 adiciona o historico paginado de evidencias Community Trust
do proprio usuario autenticado.

Endpoint:

`GET /api/v1/me/trust/evidence`

## Self-only

A identidade da conta continua derivada exclusivamente de
`X-User-Session`.

O endpoint nao aceita seletor de conta em:

- path;
- query;
- body.

Nao existe endpoint de detalhe por evidence ID nesta etapa.

## Projecao publica

Cada item retorna somente:

- `tipo_evidencia`;
- `classificacao`;
- `ocorrido_em`.

Nao sao retornados:

- `conta_id`;
- evidence UUID;
- chave de idempotencia;
- `origem`;
- `origem_id`;
- motivo interno;
- policy version;
- metadata;
- `criado_em`;
- moderator actor;
- detalhes internos da policy.

## Query-level Data Minimization

A minimizacao ocorre no SQL.

A query seleciona apenas:

- `tipo_evidencia`;
- `classificacao`;
- `ocorrido_em`.

O `id` interno e usado exclusivamente como desempate de ordenacao
e nao e retornado.

A camada User-Facing nao carrega o objeto bruto da evidencia.

## Ordenacao

O historico usa:

1. `ocorrido_em DESC`;
2. `id DESC` apenas como desempate interno.

## Paginacao

Defaults:

- `limite=20`;
- `offset=0`.

Limites:

- `limite`: 1 ate 100;
- `offset`: maior ou igual a zero.

A resposta inclui:

- `itens`;
- `limite`;
- `offset`;
- `quantidade`.

`quantidade` representa apenas o tamanho da pagina atual.

Nao existe query adicional de total global nesta etapa.

## Persistencia

Continua sendo usado:

`CommunityTrustReadOnlyRepository`

Garantias:

- SQLite `mode=ro`;
- `PRAGMA query_only = ON`;
- lifecycle explicito via `contextlib.closing`;
- nenhuma criacao de schema;
- nenhum metodo de escrita.

## AEGIS Security Impact Review

A 8F3 amplia deliberadamente a superficie autenticada com um
novo GET.

A superficie e limitada por:

- auth de infraestrutura existente quando configurada;
- User-Facing session obrigatoria;
- sujeito derivado server-side;
- self-only;
- ausencia de account selector;
- ausencia de endpoint de detalhe;
- bounded pagination;
- query-level Data Minimization;
- repository estritamente read-only;
- `Cache-Control: no-store`;
- GET only.

A API nao expoe o objeto interno de evidencia.

Nenhuma protecao existente e silenciosamente enfraquecida.

## Fora de escopo

Permanecem fora da 8F3:

- Public App Trust client;
- Public App Trust UI.

Esses itens pertencem respectivamente a 8F4 e 8F5.

## Arvore 8F

- 8F1 - completed;
- 8F2 - completed;
- 8F3 - Trust Evidence History API;
- 8F4 - Public App Trust Client;
- 8F5 - Public App Trust Surface;
- 8F6 - Final Closure.

Nao existem subniveis escondidos.

## Validacao final

A 8F3 foi validada sobre o baseline `2a55c56`.

API:

- `GET /api/v1/me/trust/evidence`;
- `X-User-Session` obrigatorio;
- Bearer de infraestrutura preservado quando configurado;
- historico exclusivamente self-only;
- sujeito derivado server-side da sessao;
- nenhum seletor horizontal de conta;
- nenhum endpoint de detalhe por evidence ID;
- GET only;
- `Cache-Control: no-store`.

Paginacao:

- `limite=20` por padrao;
- limite minimo 1;
- limite maximo 100;
- `offset=0` por padrao;
- offset minimo 0;
- sem query adicional de total global.

Data Minimization:

A query SQL seleciona somente:

- `tipo_evidencia`;
- `classificacao`;
- `ocorrido_em`.

Nao sao expostos:

- `conta_id`;
- evidence ID;
- chave de idempotencia;
- `origem`;
- `origem_id`;
- motivo interno;
- policy version;
- metadata;
- `criado_em`;
- moderator actor;
- policy internals.

O ID interno e usado apenas como desempate de ordenacao e nunca
e retornado.

Persistencia:

- repository estritamente read-only;
- SQLite `mode=ro`;
- `PRAGMA query_only = ON`;
- lifecycle explicito por `contextlib.closing`;
- nenhuma schema activation;
- nenhum write path novo.

Validacao de testes pre-closure:

- 19 testes isolados 8F3 aprovados;
- 148 testes Community Trust aprovados;
- 259 testes Servidor API aprovados;
- 194 testes Community Moderation aprovados;
- 61 testes Public Mobile aprovados;
- 70 testes backend Reporting aprovados.

A expectativa inicial de 17 casos 8F3 estava incorreta.
A suite real continha 19 testes e todos foram preservados.
Nenhum teste foi removido ou relaxado.

Live:

- `query_only` ativo;
- integrity check `ok`;
- zero foreign key errors;
- schema version 43;
- 0 moderation reports;
- 0 moderation decisions;
- 2 Trust evidence;
- 1 Trust profile;
- 2 linhas no historico publico live;
- somente campos publicos materializados;
- account ID interno nao impresso;
- SHA-256 do banco inalterado;
- nenhuma escrita live;
- nenhuma alteracao de schema live.

## Security Impact Review - Protocolo AEGIS

A superficie autenticada introduzida pela 8F3 foi explicitamente
reconhecida e limitada.

Foram validados:

- Zero Trust;
- Least Privilege;
- Defense in Depth;
- Data Minimization;
- Fail Closed;
- auth de infraestrutura existente;
- User-Facing session existente;
- self-only;
- sujeito derivado server-side;
- ausencia de seletor horizontal de conta;
- query-level Data Minimization;
- bounded pagination;
- ausencia de endpoint de detalhe;
- repository estritamente read-only;
- response `no-store`;
- ausencia de write path novo.

Nenhum contexto interno sensivel foi exposto.

Nenhuma protecao existente foi silenciosamente enfraquecida.

## Proximo passo

8F4 - Public App Trust Client.
