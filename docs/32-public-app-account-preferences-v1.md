# Fase 2 — Etapa 2 — Public App Account / Preferences V1

## Objetivo

Este bloco conecta a conta autenticada e as preferências pessoais ao
aplicativo.

Entra a rota:

```text
/account
```

## Dados da conta

A tela usa o `snapshot.account` mantido pelo Auth Session V1.

Quando disponível, mostra:

- e-mail;
- identificador público da conta.

A sessão não é renderizada.

Existe uma ação manual `Atualizar dados da conta`, que chama o fluxo já
existente de `refreshMe()` e revalida `GET /me`.

## Preferências

A tela consome:

```text
GET   /api/v1/me/preferences
PATCH /api/v1/me/preferences
```

Campos suportados:

```text
notificacoes_preco_habilitadas
marketplaces_preferidos
```

### Notificações de preço

A preferência é editada por um `Switch`.

Ela controla a elegibilidade futura para matching personalizado já existente
no backend.

### Marketplaces preferidos

A UI aceita texto separado por vírgulas.

Antes de enviar:

- espaços são removidos;
- entradas vazias são descartadas;
- duplicatas são removidas.

Lista vazia significa não restringir preferências por marketplace.

A normalização final do domínio continua pertencendo ao backend.

## Cache

Após `PATCH`, a query de preferências é invalidada para buscar o estado
persistido.

## Segurança

A UI não envia:

- `conta_id`;
- `Authorization`;
- `X-User-Session`.

Também não renderiza credenciais.

A identidade permanece resolvida exclusivamente pela sessão já isolada na
camada de transporte.

## Ações auxiliares

A tela também oferece:

- configuração local da conexão;
- logout.

## Fora deste bloco

Continuam fora:

- UI de alertas;
- Device Registration;
- Push Dispatcher;
- Personalized Feed.

O próximo bloco é `PUBLIC_APP_MVP_ALERTS_V1`.
