# User-Facing API V1 — Logout + Me V1

## Objetivo

Abrir as primeiras rotas autenticadas por sessão de usuário:

- `POST /api/v1/auth/logout`;
- `GET /api/v1/me`.

Essas rotas usam `X-User-Session` e preservam a camada separada de acesso de
infraestrutura.

## GET /api/v1/me

Exemplo:

```http
GET /api/v1/me
X-User-Session: pra_usr_v1_<token>
```

Quando a proteção de infraestrutura estiver ativa, também é necessário:

```http
Authorization: Bearer <API_APLICACAO_TOKEN>
```

A conta retornada é resolvida exclusivamente pela sessão no servidor.

`conta_id`, query string ou qualquer outro identificador enviado pelo cliente
não escolhem a conta de `/me`.

Resposta estrutural:

```json
{
  "api_version": "v1",
  "dados": {
    "conta": {
      "id": "usr_...",
      "email": "usuario@example.com",
      "criado_em": "...",
      "ativa": true
    }
  }
}
```

O token da sessão não é devolvido por `/me`.

## POST /api/v1/auth/logout

Exemplo:

```http
POST /api/v1/auth/logout
X-User-Session: pra_usr_v1_<token>
```

O logout:

- exige sessão válida;
- revoga somente o token atual;
- não encerra outras sessões da mesma conta;
- faz o token revogado falhar fechado em novas requisições.

Sucesso:

```json
{
  "api_version": "v1",
  "dados": {
    "sessao_revogada": true
  }
}
```

## Segurança

A ordem lógica permanece:

```text
acesso de infraestrutura
        ↓
sessão do usuário
        ↓
identidade resolvida server-side
        ↓
rota autenticada
```

A sessão do usuário não substitui o Bearer de infraestrutura.

## Fronteiras

Este bloco ainda não implementa:

- preferências via HTTP;
- watchlist via HTTP;
- device registration;
- push;
- feed personalizado.

As rotas read-only anteriores permanecem inalteradas.
