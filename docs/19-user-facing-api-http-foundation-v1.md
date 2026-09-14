# User-Facing API V1 — HTTP Foundation V1

## Objetivo

Implementar a infraestrutura HTTP compartilhada que será usada pelas rotas de
usuário da Fase 2, sem abrir ainda rotas de negócio como cadastro ou login.

## Componentes

### Parsing JSON

A fundação aceita payloads somente como:

```http
Content-Type: application/json
```

Regras:

- `Content-Length` é obrigatório;
- o corpo deve ser UTF-8 válido;
- JSON precisa ser um objeto;
- limite padrão: 64 KiB;
- payload incompleto falha fechado.

Erros de parsing são convertidos em erros HTTP estruturados.

### Envelope de sucesso

Formato preparado para futuras rotas user-facing:

```json
{
  "api_version": "v1",
  "dados": {}
}
```

### Envelope de erro

```json
{
  "api_version": "v1",
  "erro": {
    "codigo": "codigo_estavel",
    "mensagem": "Mensagem segura para o cliente."
  }
}
```

O envelope novo é reservado à superfície user-facing. As rotas read-only
existentes não são alteradas neste estágio.

## Sessão do usuário

A fundação extrai:

```http
X-User-Session: pra_usr_v1_<token>
```

Valida formato e tamanho antes de consultar a camada de identidade.

Para uma rota autenticada, o token é resolvido server-side por
`UserIdentityService.resolver_sessao`.

Se a sessão estiver ausente, inválida, revogada, expirada ou associada a uma
conta que não pode ser resolvida, a operação falha fechada.

## Serviço de identidade opcional no servidor

`ServidorApiAplicacao` agora pode receber `user_identity_service`.

Essa dependência é opcional para preservar compatibilidade com o runtime e
com as rotas read-only atuais.

Enquanto nenhuma rota user-facing estiver ativa, o runtime atual não precisa
ser alterado.

Quando as rotas autenticadas forem implementadas, o runtime deverá injetar o
serviço real de identidade.

## Limites

Este bloco não implementa:

- `POST /api/v1/auth/register`;
- `POST /api/v1/auth/login`;
- `POST /api/v1/auth/logout`;
- `GET /api/v1/me`;
- preferências via HTTP;
- watchlist via HTTP.

Também não altera:

- Bearer de infraestrutura;
- política de loopback/remoto;
- rotas de produtos;
- histórico;
- alertas;
- health;
- control plane administrativo.

## Próximo passo

Implementar `register/login` sobre esta fundação, com o serviço de identidade
injetado de forma explícita no runtime.
