# User-Facing API V1 — Watchlist HTTP V1

Rotas autenticadas:

- `GET /api/v1/me/watchlist`;
- `PUT /api/v1/me/watchlist/{canonical_key}`;
- `DELETE /api/v1/me/watchlist/{canonical_key}`.

A identidade vem exclusivamente de `X-User-Session`.

O `PUT` faz upsert. O corpo aceita somente `preco_alvo` e
`notificar_queda_preco`. `conta_id`, `canonical_key`, ids internos e campos
desconhecidos são rejeitados.

`preco_alvo` é devolvido como string decimal ou `null`, evitando perda de
precisão monetária.

O `DELETE` remove somente o item da conta autenticada. Se a chave não existir
para aquela conta, retorna `404`, mesmo que exista na watchlist de outro usuário.

A proteção `Authorization: Bearer <API_APLICACAO_TOKEN>` continua separada e
preservada quando configurada.

Depois deste bloco, o próximo endurecimento da Etapa 1 é rate limiting / abuse
controls antes do audit final.
