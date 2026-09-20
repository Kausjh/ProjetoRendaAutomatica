# Missions Read API V1 - 7E

## Objetivo

Expor ao usuario autenticado o estado atual das missoes sem permitir
qualquer escrita client-side sobre progresso, conclusao ou rewards.

A rota planejada para a camada HTTP e:

`GET /api/v1/me/missions`

## Fonte de verdade

A leitura combina tres fontes server-side ja existentes:

1. catalogo de missoes de producao;
2. tabela `mission_progress`;
3. tabela `mission_reward_grants`.

O cliente nao calcula progresso e nao decide se uma missao esta concluida.

## Estado de reward

A API de leitura usa apenas tres estados de apresentacao:

- `locked`: a missao ainda nao gerou reward;
- `pending`: entitlement criado, settlement ainda pendente;
- `granted`: reward liquidado no ledger de Gamification.

IDs internos de reward grant e referencias internas de Gamification nao
fazem parte do contrato publico.

## Seguranca

A identidade deve vir exclusivamente da sessao de usuario.

O cliente nao pode fornecer `conta_id` para escolher outra conta.

A infraestrutura Bearer existente continua preservada.

## Fronteiras

A 7E nao:

- cria ou altera progresso;
- conclui missoes;
- concede XP;
- liquida rewards;
- altera reputacao;
- expoe historico bruto de eventos;
- altera score de ofertas;
- altera Price Intelligence;
- implementa a tela do aplicativo.

A integracao visual continua reservada para a 7F.

## Implementacao 7E1

A primeira parte da 7E adiciona:

- lookup publico account-scoped de reward no MissionRepository;
- leitura equivalente no MissionService;
- `MissionReadService`;
- contrato HTTP V1;
- testes do core de leitura.

## Implementacao 7E2

A segunda parte da 7E adiciona:

- `UserFacingMissionsController`;
- `GET /api/v1/me/missions`;
- identidade derivada exclusivamente de `X-User-Session`;
- preservacao do Bearer de infraestrutura;
- injecao do `MissionReadService` pelo runtime;
- resposta no envelope user-facing existente;
- erro 503 quando o Mission Runtime nao fornece o read service.

O parametro `conta_id` enviado pelo cliente nao seleciona outra conta.
A conta usada pela leitura sempre vem da sessao autenticada.

## Validacao operacional

A validacao real foi concluida em 20/09/2026 sobre o commit `cba7423`.

O runtime foi reciclado cirurgicamente e voltou como PID `16144`, com
o supervisor preservado e a Application API saudavel.

O smoke autenticado confirmou:

- `GET /api/v1/me/missions` com HTTP 200;
- ruleset `missions-community-rewards-production-v1`;
- 3 missoes retornadas;
- 1 missao concluida e 2 em andamento;
- 1 reward `granted` e 0 `pending`;
- estado real de progresso e rewards serializado corretamente;
- nenhuma alteracao em missions ou Gamification causada pela leitura;
- sessao temporaria revogada ao final;
- SQLite integro;
- 0 erros de foreign key.

## Estado atual

A 7E esta concluida e validada em producao.

O servidor continua sendo a unica autoridade sobre progresso,
conclusao e rewards. O cliente recebe apenas uma representacao
somente-leitura desse estado.

## Proximo passo

**7F - Public App Missions Surface**

Consumir `GET /api/v1/me/missions` no aplicativo e apresentar o estado
das missoes sem recalcular progresso ou recompensas no cliente.
