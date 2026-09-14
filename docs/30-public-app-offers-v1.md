# Fase 2 — Etapa 2 — Public App Offers V1

## Objetivo

Este bloco conecta o aplicativo público às rotas read-only de catálogo já
existentes.

Entram:

- lista de produtos;
- detalhe por chave canônica;
- histórico de preços;
- loading;
- erro;
- estado vazio;
- pull-to-refresh.

## Rotas do app

```text
/home
/product/[canonicalKey]
```

`/home` continua protegido pelo estado local de autenticação do aplicativo.

O backend de catálogo permanece usando apenas a proteção de infraestrutura já
definida para as rotas read-only. O app não inventa `X-User-Session` nessas
chamadas.

## Rotas HTTP

```text
GET /api/v1/produtos
GET /api/v1/produtos/{canonical_key}
GET /api/v1/produtos/{canonical_key}/historico
```

## Camada de apresentação

A UI não consome diretamente o JSON bruto.

`src/offers/offer-presenter.ts` converte payloads read-only em modelos simples
do app.

Essa camada tolera:

- campos opcionais;
- algumas variações de nomes legadas;
- listas encapsuladas ou em array direto;
- preço numérico ou string numérica;
- ausência de desconto;
- ausência de marketplace.

A chave canônica continua obrigatória para itens da lista.

## Lista

A tela `/home` mostra até 50 produtos por carga inicial.

Cada card tenta exibir:

- título;
- preço atual;
- preço original;
- desconto;
- marketplace;
- entrada para detalhe.

A tela possui pull-to-refresh e retry explícito.

## Detalhe

O detalhe usa a chave canônica na URL do Expo Router.

São exibidos os dados públicos normalizados e o histórico de preços.

## Histórico

O histórico mostra, quando disponíveis:

- preço;
- marketplace;
- timestamp formatado em `pt-BR`.

## Segurança

Nenhuma credencial é renderizada.

A UI continua sem conhecer Bearer, `X-User-Session`, IP ou implementação do
transporte.

## Fora deste bloco

Continuam fora:

- abertura de link externo do marketplace;
- watchlist;
- preferências;
- alertas;
- Device Registration;
- Push Dispatcher;
- Personalized Feed.

O próximo bloco é `PUBLIC_APP_MVP_WATCHLIST_V1`.
