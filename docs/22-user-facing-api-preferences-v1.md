# User-Facing API V1 — Preferences HTTP V1

## Objetivo

Expor as preferências pessoais da conta autenticada sem permitir que o cliente
escolha outra conta por `conta_id`.

Rotas:

- `GET /api/v1/me/preferences`;
- `PATCH /api/v1/me/preferences`.

As duas exigem `X-User-Session`. Quando a proteção de infraestrutura estiver
ativa, também exigem `Authorization: Bearer <API_APLICACAO_TOKEN>`.

## GET

Na primeira leitura, caso ainda não exista registro persistido, o serviço cria
os defaults já definidos pela fundação de personalização:

```json
{
  "notificacoes_preco_habilitadas": true,
  "marketplaces_preferidos": []
}
```

## PATCH

O PATCH é parcial: campo omitido conserva o valor anterior.

A camada HTTP rejeita payload vazio, campos desconhecidos, `conta_id`,
booleanos enviados como string e marketplaces que não sejam lista de strings.

Normalização, deduplicação e limites permanecem no
`UserPersonalizationService`.

## Isolamento

A conta vem exclusivamente de `X-User-Session`. O cliente não seleciona conta
por body, query string ou path.

## Runtime

`UserPersonalizationRepository` e `UserPersonalizationService` usam o mesmo
`database/user_identity.sqlite3` da identidade, preservando as FKs para
`contas_usuario`.

## Fronteiras

A watchlist continua fora da API HTTP neste bloco.

Também não entram device registration, push ou feed personalizado.
