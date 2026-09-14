# Fase 2 — Etapa 2 — Public App Watchlist V1

## Objetivo

Este bloco conecta a watchlist pessoal do usuário ao aplicativo.

Entram:

- listagem da watchlist;
- adicionar produto;
- atualizar configurações;
- remover produto;
- preço-alvo opcional;
- opção `notificar_queda_preco`;
- refresh e invalidação de cache após mutações.

## API usada

```text
GET    /api/v1/me/watchlist
PUT    /api/v1/me/watchlist/{canonical_key}
DELETE /api/v1/me/watchlist/{canonical_key}
```

Essas rotas exigem sessão de usuário.

O app não envia `conta_id`. A identidade continua sendo resolvida
exclusivamente pelo `X-User-Session` no transporte.

## Tela `/watchlist`

A tela mostra os itens acompanhados.

Cada item exibe:

- chave canônica;
- preço-alvo, quando definido;
- estado de acompanhamento de queda de preço.

O item abre o detalhe do produto.

A tela possui pull-to-refresh, estado vazio, loading e retry.

## Edição no detalhe do produto

A própria tela de produto ganha uma seção `Acompanhar produto`.

Campos:

```text
Preço-alvo
Notificar queda de preço
```

Preço-alvo vazio é enviado como `null`.

Quando preenchido, precisa ser numérico e maior que zero.

## Upsert

Salvar usa `PUT`.

O mesmo fluxo serve para criar ou atualizar o item.

Após sucesso, a query da watchlist é invalidada para buscar o estado
persistido pelo backend.

## Remoção

Quando o produto já está na watchlist, a tela exibe `Remover da watchlist`.

A remoção usa `DELETE`.

Após sucesso, o cache também é invalidado.

## Segurança

A UI não manipula diretamente:

- `conta_id`;
- `Authorization`;
- `X-User-Session`;
- token de usuário;
- Bearer de infraestrutura.

Esses detalhes continuam isolados na camada de transporte.

## Fora deste bloco

Continuam fora:

- preferências da conta;
- alertas;
- Device Registration;
- Push Dispatcher;
- Personalized Feed.

O próximo bloco é `PUBLIC_APP_MVP_ACCOUNT_PREFERENCES_V1`.
