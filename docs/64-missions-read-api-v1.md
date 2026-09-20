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

## Proximo passo

Validar a rota no runtime real e executar um smoke controlado antes de
fechar formalmente a 7E e seguir para a 7F.
