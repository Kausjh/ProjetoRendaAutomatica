# Missions & Community Rewards V1 - Controlled Runtime Wiring 7D3

## Status

7D3 implementada localmente.

O Runtime Unificado conhece o Reward Settlement, mas a feature flag permanece
desligada por padrao.

Nenhum reward real e liquidado nesta subetapa.

## Feature flag

`RUNTIME_MISSION_REWARD_SETTLEMENT_ATIVO`

Default: `False`.

`ConfiguracoesRuntime.carregar()` carrega o `.env` antes de resolver a flag.

Sem valor explicitamente verdadeiro, o settlement nao roda.

## Ordem

1. Gamification reconciliation;
2. Missions reconciliation;
3. Reward Settlement, somente com a feature flag ativa;
4. Personalized Feed;
5. API e restante do runtime.

## Preconditions

Mesmo com a feature flag ligada, o settlement so executa se:

- Gamification estiver ativo;
- Missions estiver ativo;
- `MissionService` estiver disponivel.

Caso contrario, o settlement e bloqueado.

## Falhas

Falha do settlement nao encerra o Runtime Unificado.

O erro e registrado e um futuro restart pode repetir o processamento.

A estrategia `recoverable-two-step` permanece responsavel por impedir
duplicacao de XP.

## Baseline real antes da ativacao

- 1 reward pending;
- 20 XP pendentes;
- 0 granted;
- 0 eventos mission_reward;
- 140 XP;
- 7 eventos de gamification;
- reputacao 0.

## Primeira ativacao controlada esperada

Se a baseline continuar igual:

- pending deve ir de 1 para 0;
- granted deve ir de 0 para 1;
- deve surgir 1 evento mission_reward;
- XP deve ir de 140 para 160;
- eventos devem ir de 7 para 8;
- reputacao deve continuar 0.

## Fronteiras

A 7D3 nao:

- liga a feature flag;
- modifica `.env`;
- reinicia runtime;
- liquida reward real;
- altera reputacao;
- altera Public App;
- altera API;
- altera offer scoring;
- altera Price Intelligence.

## Proximo passo

7D4 - Controlled Production Activation.

A 7D4 deve criar backup pre-ativacao, habilitar a flag de forma controlada,
reciclar somente o runtime necessario, comprovar o settlement real e provar
que uma segunda reconciliacao e neutra.
