# Community Moderation User Report Creation V1 - 8E10A

## Status

8E10A CONCLUIDA E VALIDADA.

## Rota

`POST /api/v1/me/reports`

## Autenticacao

A rota reutiliza a autenticacao de usuario existente por
`X-User-Session`.

`reporter_conta_id` e derivado exclusivamente da sessao autenticada.

A protecao de infraestrutura existente por `API_APLICACAO_TOKEN`
permanece preservada.

## Payload

Campos aceitos:

- `target_id`;
- `motivo`;
- `detalhes`.

O cliente nao controla:

- `reporter_conta_id`;
- `target_type`;
- estado;
- timestamp;
- moderator actor;
- authority origin;
- familia Trust.

`target_type` e derivado no servidor como `community_discovery`.

## Persistencia

A escrita reutiliza `CommunityModerationRepository`.

O repository:

- valida reporter;
- valida a community discovery;
- gera o ID `rpt_...` no servidor;
- persiste estado inicial `received`.

Criar uma denuncia nao cria decisao administrativa e nao escreve Trust.

## Runtime

O repository e injetado na User-Facing API somente quando o runtime de
Community Moderation esta ativo.

Quando a flag esta OFF, o controller recebe `None` e a rota falha
fechado com HTTP 503.

A 8E10A nao altera a feature flag e nao executa reconciliation.

## 8E10B

O repository ja possui replay semantico interno.

A politica publica de idempotencia e protecao contra duplicatas fica
reservada para 8E10B.

A 8E10A nao adiciona `Idempotency-Key`.

## 8E10C

A 8E10A nao cria leitura/status de denuncias.

Read-back limitado fica reservado para 8E10C.

## Validacao

A persistencia real da 8E10A e testada somente contra SQLite
temporario.

Nao ha escrita no banco live, restart ou canario nesta etapa.

## Validacao final

A 8E10A foi validada integralmente sobre o baseline `ed66a5d`.

Resultados pre-closure:

- 3/3 repeticoes verdes do teste HTTP antigo 8E9C que havia sofrido
  `WinError 10053`;
- 21 testes da 8E9C aprovados;
- 25 casos isolados da 8E10A aprovados;
- 186 casos acumulados 8E1..8E10A aprovados;
- 235 casos Trust + Moderation + Reporting aprovados;
- 96 casos do servidor administrativo aprovados;
- 178 casos do servidor User-Facing aprovados;
- pre-commit aprovado.

Estado live:

- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros de foreign key;
- nenhuma escrita live.

A protecao de infraestrutura existente foi preservada.

A criacao autenticada deriva reporter da sessao e target type no
servidor.

A criacao de report nao cria decision e nao escreve Trust.

Idempotencia/duplicate protection publica fica para 8E10B.

Read-back de status do usuario fica para 8E10C.

## Proximo passo

8E10B - Idempotency / Duplicate Protection.
