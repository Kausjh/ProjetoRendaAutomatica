# Fase 2 — Etapa 2 — Public App API Client / Transport V1

## Objetivo

Este bloco cria a camada HTTP real do Public App sem acoplar a UI ao transporte.

O código vive em:

```text
apps/public-mobile/src/api/
```

## Credenciais

O transporte possui duas credenciais independentes.

### Infraestrutura

```http
Authorization: Bearer <token-local>
```

O token é carregado da configuração local persistida em Secure Store.

Ele não é hardcoded, não é lido de `EXPO_PUBLIC_*` e não identifica a conta do
usuário.

### Sessão do usuário

```http
X-User-Session: pra_usr_v1_<token>
```

Esse header só é enviado quando a operação exige usuário autenticado.

## Base URL

A configuração local deve fornecer uma URL completa terminando em:

```text
/api/v1
```

Exemplo conceitual:

```text
http://<endpoint-confiavel>:<porta>/api/v1
```

Nenhum IP, hostname ou token real é versionado.

A porta administrativa `8765` é rejeitada pela validação de configuração.

## Modos de resposta

A API atual possui duas superfícies de resposta.

### Rotas read-only já existentes

Produtos, histórico, alertas e health continuam sendo tratados como JSON bruto,
preservando o contrato V1 já existente.

### Rotas user-facing

Cadastro, login, logout, `/me`, preferências e watchlist usam o envelope:

```json
{
  "api_version": "v1",
  "dados": {}
}
```

Em erro, o client preserva status HTTP, código/mensagem do envelope e
`Retry-After` quando disponível.

## Resiliência

O transporte implementa:

- timeout com `AbortController`;
- mapeamento de falha de rede;
- validação de JSON;
- preservação de `Retry-After`;
- codificação de query string;
- `encodeURIComponent` para chaves canônicas nas URLs.

Nenhuma credencial é registrada em log.

## Separação da UI

As telas não conhecem:

- Tailscale;
- porta de forward;
- IP do host;
- `Authorization`;
- `X-User-Session`.

Elas consumirāo `PublicApiClient`.

## Fora deste bloco

Ainda não entram:

- telas de login/cadastro;
- estado global de autenticação;
- limpeza automática de sessão após logout;
- Device Registration;
- push;
- Personalized Feed.

O próximo bloco é `PUBLIC_APP_MVP_AUTH_SESSION_V1`.
