# Etapa 3 — Device Registration V1 — Fase A

## Objetivo

Esta fase implementa a fundação de backend do Device Registration V1.

O objetivo é permitir que o backend associe instalações do aplicativo público a
uma conta autenticada, mantenha múltiplos dispositivos por conta, aceite rotação
de token e represente o estado ativo/inativo sem enviar push ainda.

## Identidade e autorização

A conta é derivada exclusivamente da sessão `X-User-Session`.

O cliente não envia `conta_id` para escolher a conta. As rotas operam somente
sobre os dispositivos pertencentes ao usuário autenticado.

## Rotas

- `GET /api/v1/me/devices`
  - lista os dispositivos da conta autenticada;
- `PUT /api/v1/me/devices/{instalacao_id}`
  - registra uma nova instalação;
  - reativa uma instalação previamente revogada;
  - rotaciona o token da mesma instalação quando o token muda;
- `DELETE /api/v1/me/devices/{instalacao_id}`
  - marca a instalação como inativa.

O `PUT` recebe somente:

```json
{
  "plataforma": "android",
  "push_token": "token-opaco"
}
```

## Persistência

A tabela `dispositivos_usuario` vive no mesmo banco lógico de identidade:

`database/user_identity.sqlite3`

Cada instalação é única por:

`conta_id + instalacao_id`

O hash do token é único globalmente para impedir que o mesmo token seja
silenciosamente associado a outra instalação.

O token bruto precisa permanecer persistido porque o dispatcher futuro deverá
entregá-lo ao provedor de push. Ele não é devolvido pela API e o modelo o omite
da representação padrão para reduzir exposição acidental em logs.

## Rotação

Registrar novamente o mesmo `instalacao_id`:

- preserva o id interno do dispositivo;
- atualiza plataforma e token;
- reativa o dispositivo;
- limpa `revogado_em`;
- informa se ocorreu rotação de token.

## Estado ativo/inativo

A revogação não apaga o registro.

Ela define:

- `ativo = false`;
- `revogado_em`;
- `atualizado_em`.

Uma nova operação `PUT` para a mesma instalação pode reativá-la.

## Fronteiras desta fase

Esta fase:

- não envia push;
- não configura Firebase, APNs, Expo Push Service ou outro provedor;
- não faz chamadas de rede externas;
- não expõe credenciais de provedor;
- não implementa ainda aquisição automática do token no app público;
- não implementa ainda registro automático no bootstrap do app.

A aquisição do token pelo aplicativo e o vínculo automático com estas rotas são
a próxima fase do Device Registration V1.

## Compatibilidade com o Bloco 30

O contrato e a documentação do Personalized Notification Outbox V1 permanecem
inalterados porque registram corretamente as fronteiras históricas daquele
bloco. O Device Registration V1 é um consumidor posterior dessa fundação.

## Critérios cobertos nesta fase

1. modelo persistente de dispositivo;
2. múltiplos dispositivos por conta;
3. registro idempotente por instalação;
4. rotação de token;
5. revogação e reativação;
6. estado ativo/inativo;
7. isolamento por conta;
8. token não exposto pela API;
9. nenhuma entrega de push real.
