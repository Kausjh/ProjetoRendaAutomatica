# User-Facing API V1 — Contrato de autenticação

## Objetivo

Este documento define a fronteira de autenticação da primeira etapa da Fase 2.

Nenhuma rota nova é criada neste bloco. A finalidade é estabilizar o contrato
antes da implementação HTTP.

## Problema

A Application API já possui uma credencial Bearer própria, usada para proteger
o acesso à infraestrutura:

```http
Authorization: Bearer <API_APLICACAO_TOKEN>
```

Essa credencial não representa uma pessoa.

A fundação de identidade também possui sessões de usuário próprias, com tokens
opacos prefixados por `pra_usr_v1_`, expiração, revogação e persistência
somente do hash.

Usar `Authorization: Bearer` para ambos criaria ambiguidade e acoplamento entre
segurança de transporte e identidade.

## Modelo oficial: duas camadas

### Camada 1 — Infrastructure Access Guard

Header:

```http
Authorization: Bearer <API_APLICACAO_TOKEN>
```

Responsabilidade:

- proteger a entrada na Application API;
- seguir a política já existente de acesso do cliente;
- ser opcional em loopback conforme contrato atual;
- ser obrigatória fora de loopback conforme contrato atual.

Essa credencial nunca identifica o usuário final.

### Camada 2 — End-User Session

Header:

```http
X-User-Session: pra_usr_v1_<token-opaco>
```

Responsabilidade:

- identificar a conta autenticada;
- resolver a sessão no servidor;
- respeitar expiração;
- respeitar revogação;
- falhar fechada para conta inexistente ou inativa.

O token de sessão nunca substitui a proteção de infraestrutura.

## Matriz de autenticação

| Rota | Infraestrutura | Sessão do usuário |
| --- | --- | --- |
| `POST /api/v1/auth/register` | conforme política de transporte | não |
| `POST /api/v1/auth/login` | conforme política de transporte | não |
| `POST /api/v1/auth/logout` | conforme política de transporte | sim |
| `GET /api/v1/me` | conforme política de transporte | sim |
| `GET /api/v1/me/preferences` | conforme política de transporte | sim |
| `PATCH /api/v1/me/preferences` | conforme política de transporte | sim |
| `GET /api/v1/me/watchlist` | conforme política de transporte | sim |
| `PUT /api/v1/me/watchlist/{canonical_key}` | conforme política de transporte | sim |
| `DELETE /api/v1/me/watchlist/{canonical_key}` | conforme política de transporte | sim |

"Conforme política de transporte" significa preservar o comportamento atual:
loopback pode dispensar o Bearer de infraestrutura; acesso remoto não pode.

## Regra de identidade para `/me`

Rotas sob `/me` nunca aceitam `conta_id` fornecido pelo cliente para decidir
qual conta será manipulada.

A identidade deve vir exclusivamente da resolução de `X-User-Session`.

Isso elimina uma classe inteira de falhas de autorização horizontal em que um
cliente tenta trocar o identificador da conta no payload ou na query string.

## Sessão

A sessão V1 é opaca.

O servidor:

1. recebe `X-User-Session`;
2. calcula o hash do token;
3. procura a sessão persistida;
4. rejeita sessão ausente, revogada ou expirada;
5. resolve a conta;
6. rejeita conta inexistente ou inativa;
7. fornece internamente o `conta_id` para a operação.

O token em texto puro não deve ser persistido nem colocado em logs.

## Logout

`POST /api/v1/auth/logout` revoga somente a sessão apresentada em
`X-User-Session`.

Logout não altera `API_APLICACAO_TOKEN`, não encerra o control plane e não
revoga automaticamente outras sessões do usuário.

Revogação global de sessões pode ser uma capacidade futura e deve possuir
contrato próprio.

## Erros V1

- `401`: credencial de infraestrutura ausente/inválida quando exigida;
- `401`: sessão de usuário ausente/inválida/expirada/revogada;
- `404`: recurso pertencente a outro usuário não deve ser revelado;
- `409`: tentativa de cadastrar email já existente;
- `400`: payload inválido;
- `405`: método não suportado.

Para isolamento entre usuários, preferimos não revelar a existência de um
recurso que pertence a outra conta.

## CSRF

A sessão de usuário V1 não usa cookie.

Como o token precisa ser enviado explicitamente em `X-User-Session`, o modelo
V1 não depende de proteção CSRF baseada em token adicional.

Se uma interface web futura migrar a sessão para cookie, essa decisão deverá
reabrir a análise de CSRF.

## Logging e segredos

Nunca registrar:

- senha;
- `X-User-Session`;
- token de sessão em payload;
- `API_APLICACAO_TOKEN`;
- credenciais administrativas.

Tokens não devem aparecer em URL ou query string.

## Control plane

A API administrativa permanece fora da User-Facing API.

Nenhuma rota de usuário deve delegar autorização ao control plane e nenhum
token administrativo deve ser entregue ao cliente público.

## O que este bloco NÃO faz

Este bloco não:

- implementa `register`;
- implementa `login`;
- implementa `logout`;
- implementa `/me`;
- implementa preferências via HTTP;
- implementa watchlist via HTTP;
- altera a política de rotas read-only existentes;
- altera o control plane;
- cria push;
- cria app público.

## Próximo passo

Implementar a infraestrutura HTTP compartilhada da User-Facing API V1:

1. parsing JSON;
2. envelope de respostas e erros;
3. extração de `X-User-Session`;
4. resolução de sessão;
5. testes de fronteira.

Depois disso entram `register/login`.
