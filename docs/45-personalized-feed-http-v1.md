# Personalized Feed V1 - HTTP

## Fase 5B

A Fase 5B expoe o motor da Fase 5A pela Application API.

Rota: `GET /api/v1/me/feed`

A identidade vem exclusivamente de `X-User-Session`.
`conta_id` enviado em query string nao seleciona outra conta e nao altera
a identidade resolvida pela sessao.

## Paginacao

- `limite`: padrao 20, minimo efetivo 1, maximo 50;
- `offset`: padrao 0, minimo efetivo 0.

Valores nao inteiros retornam HTTP 400 com `paginacao_invalida`.

## Seguranca

A protecao por `Authorization: Bearer <API_APLICACAO_TOKEN>` continua
independente da sessao do usuario. Quando configurada, ambas precisam ser
satisfeitas.

## Fronteiras

Esta fase nao altera o Public App, nao envia push, nao consome Notification
Outbox, nao aceita identidade escolhida pelo cliente e nao cria novo catalogo.

## Proximo passo

A Fase 5C integrara `GET /api/v1/me/feed` ao Public App.
