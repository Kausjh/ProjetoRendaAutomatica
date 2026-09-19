# Personalized Feed V1

## Fase 5A — Core Service

A Fase 5A cria o motor de feed personalizado sem abrir rota HTTP e sem
alterar o aplicativo público.

O serviço reutiliza três fundações existentes:

- personalização de usuário e watchlist;
- catálogo canônico;
- Price Intelligence.

Nenhum segundo catálogo ou banco de personalização é criado.

## Sinais de relevância

O ranking V1 é determinístico e explicável:

- produto presente na watchlist: +100;
- preço-alvo atingido: +40;
- melhor preço atual em marketplace preferido: +25.

Produtos sem qualquer sinal real da conta não entram no feed.

Empates são resolvidos por:

1. atualização mais recente;
2. `canonical_key` em ordem crescente.

## Deduplicação

A unidade lógica do feed é o produto canônico.

Portanto, o feed mantém no máximo um item por `canonical_key`, mesmo quando
o produto possui múltiplos anúncios.

## Paginação

A paginação ocorre depois da seleção, deduplicação e ordenação.

- limite padrão: 20;
- limite máximo: 50;
- offset mínimo: 0.

## Fronteiras desta fase

Esta fase deliberadamente não:

- adiciona rota HTTP;
- altera o Public App;
- consome Notification Outbox;
- envia push;
- cria personalização simulada;
- altera preferências ou watchlists existentes.

## Próximo passo

A Fase 5B deve expor o serviço autenticado em:

`GET /api/v1/me/feed`

A conta deverá ser derivada exclusivamente da sessão de usuário.
