# User-Facing API V1 — Register/Login V1

## Objetivo

Abrir as primeiras rotas reais de usuário sobre a fundação HTTP e a fundação
de identidade já existentes.

## Rotas

### Cadastro

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "usuario@example.com",
  "senha": "uma-senha-forte"
}
```

Sucesso:

- HTTP `201`;
- retorna somente dados públicos da conta;
- não cria sessão automaticamente.

O cadastro não retorna senha, hash ou salt.

Email já existente retorna `409`.

Validações de email e senha continuam pertencendo a `UserIdentityService`.

### Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "usuario@example.com",
  "senha": "uma-senha-forte"
}
```

Sucesso:

- HTTP `200`;
- retorna dados públicos da conta;
- retorna token opaco de sessão;
- retorna a expiração da sessão.

Credenciais inválidas retornam sempre erro genérico `401`.

A API não informa se foi email inexistente, conta inativa ou senha incorreta.

## Infraestrutura x usuário

As duas rotas preservam a camada de infraestrutura.

Quando `API_APLICACAO_TOKEN` estiver configurado, o cliente ainda deve enviar:

```http
Authorization: Bearer <API_APLICACAO_TOKEN>
```

Register/login não exigem `X-User-Session`, pois são justamente as rotas que
precedem uma sessão autenticada.

## Runtime

O runtime passa a construir:

```text
UserIdentityRepository
        ↓
UserIdentityService
        ↓
ServidorApiAplicacao
```

Banco:

```text
database/user_identity.sqlite3
```

O servidor recebe a mesma instância de `UserIdentityService` usada para criar,
autenticar e emitir sessões.

## Resposta de login

A sessão é retornada apenas no corpo HTTPS/HTTP protegido pelo transporte
confiável já definido para o cliente.

Exemplo estrutural:

```json
{
  "api_version": "v1",
  "dados": {
    "conta": {
      "id": "usr_...",
      "email": "usuario@example.com",
      "criado_em": "...",
      "ativa": true
    },
    "sessao": {
      "token": "pra_usr_v1_...",
      "expira_em": "..."
    }
  }
}
```

O token em texto puro não é persistido pelo backend.

## Fronteiras

Este bloco ainda não implementa:

- logout;
- `/me`;
- preferências via HTTP;
- watchlist via HTTP;
- device registration;
- push.

As rotas read-only de catálogo, preços e alertas preservam o comportamento
anterior.
