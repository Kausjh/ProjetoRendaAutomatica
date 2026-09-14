# Fase 2 — Etapa 2 — Public App Alerts V1

## Objetivo

Este bloco conecta a tela de alertas ao Alert Engine read-only já existente.

Entra a rota:

```text
/alerts
```

## API

A tela consome:

```text
GET /api/v1/alertas?limite=100&offset=0
```

A rota permanece no contrato read-only da Application API.

Ela usa a proteção de infraestrutura existente e não exige
`X-User-Session` no backend.

Mesmo assim, a tela do aplicativo continua protegida pelo estado local
`authenticated`, porque ela faz parte da área autenticada do MVP.

## Adapter

O JSON bruto não é ligado diretamente aos componentes.

`src/alerts/alert-presenter.ts` normaliza campos opcionais e variações legadas,
incluindo:

- tipo;
- mensagem;
- chave canônica;
- marketplace;
- preço anterior;
- preço atual;
- timestamp.

A ausência de campos não impede que o card seja renderizado.

## Tela

Cada alerta tenta mostrar:

- categoria legível;
- marketplace;
- horário;
- mensagem;
- transição de preço;
- chave canônica.

Quando existe `canonical_key`, o card abre:

```text
/product/[canonicalKey]
```

## Estados

A tela possui:

- loading;
- retry;
- estado vazio;
- pull-to-refresh.

## Limite semântico

Esta tela mostra eventos do Alert Engine read-only.

Ela não é:

- Personalized Feed;
- Push Dispatcher;
- Device Registration;
- outbox personalizado.

Esses recursos pertencem às etapas posteriores da Fase 2.

## Segurança

A UI não manipula:

- `Authorization`;
- `X-User-Session`;
- Bearer;
- token de sessão.

A camada de transporte continua sendo a única responsável por esses detalhes.

## Próximo passo

Com as telas funcionais do MVP presentes, o próximo bloco é:

```text
PUBLIC_APP_MVP_ANDROID_SMOKE_V1
```

Ele valida o aplicativo em execução real no Android sobre o transporte
Tailscale já definido.
