# Missions & Community Rewards V1 - Settlement Runtime 7D2

## Status

7D2 implementada localmente.

O componente de reconciliacao de settlement existe e foi testado, mas
`runtime.py` ainda nao o chama.

Nenhum reward do banco real e liquidado nesta subetapa.

## Dependencia

A 7D2 depende da 7D1:

`3dcdbaa feat: add mission reward settlement core`

## Papel do componente

`ativar_reward_settlement_runtime(...)` recebe o `MissionService` que ja foi
reconciliado pela camada de Missions.

Ele cria um `GamificationService` dedicado ao settlement usando:

- o mesmo SQLite de producao;
- o mesmo `UserIdentityRepository`;
- o ruleset composto da 7D1;
- o `MissionRewardSettlementService` da 7D1.

Em seguida executa `liquidar_pendentes()`.

## Ordem futura do runtime

Quando a 7D3 fizer o wiring em `runtime.py`, a ordem deve ser:

1. Gamification reconciliation;
2. Missions reconciliation;
3. Reward Settlement reconciliation;
4. Personalized Feed / API / restante do runtime.

Isso garante que rewards criados pela reconciliacao de Missions possam ser
liquidados antes de o runtime expor o estado final de gamification.

## Resultado

O componente retorna:

- `ativo`;
- `settlement_service`;
- `gamification_service`;
- resultado da reconciliacao;
- erro.

Se o lote terminar com qualquer falha, `ativo=False`.

O processamento anterior que ja tiver sido concluido nao e revertido, pois a
estrategia da 7D1 e deliberadamente `recoverable-two-step`. O retry permanece
seguro.

## Fronteiras

A 7D2 nao modifica:

- `runtime.py`;
- banco real;
- Public App;
- API publica;
- reputacao comunitaria;
- contributor trust;
- rankings;
- offer scoring;
- Price Intelligence.

## Proximo passo

7D3 - Controlled Runtime Wiring.

A 7D3 deve inserir o componente depois de Missions e antes de Personalized
Feed, revisar o diff, commitar e somente depois preparar uma ativacao real
controlada.

O reward real de 20 XP deve continuar `pending` ate a ativacao controlada.
