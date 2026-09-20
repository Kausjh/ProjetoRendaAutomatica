# Missions & Community Rewards V1 - 7D5 Live Reward Settlement

## Problema

A 7D4 validou o settlement de rewards no bootstrap do runtime.

Esse bootstrap recupera rewards `pending` existentes quando o runtime
inicia, mas uma nova missao pode ser concluida durante um ciclo normal
de Community Discovery enquanto o runtime permanece ativo.

Sem a 7D5, esse novo reward pode permanecer `pending` ate um restart.

## Solucao

A 7D5 adiciona um wiring composto:

1. a descoberta comunitaria e persistida como `approved`;
2. o Mission Community Wiring registra o progresso;
3. uma missao concluida pode criar um reward `pending`;
4. o Live Reward Settlement executa `liquidar_pendentes`;
5. o settlement existente cria/reutiliza o evento de Gamification;
6. o reward termina `granted`.

O sweep de pending e executado apos cada aprovacao mesmo quando aquela
aprovacao nao criou um novo reward.

Isso permite recuperar uma janela de falha anterior sem depender de
restart.

## Fail-open

A aprovacao principal continua sendo persistida antes do hook.

Falhas em:

- Mission Wiring;
- Live Reward Settlement;

nao revertem a descoberta `approved`.

O resultado do hook exp?e as falhas para logging e observabilidade.

## Idempotencia

A 7D5 nao cria uma segunda politica de settlement.

Ela reutiliza `MissionRewardSettlementService`, inclusive sua chave
deterministica baseada no reward grant ID.

Portanto uma repeticao pode:

- encontrar um reward ainda `pending`;
- encontrar o evento de Gamification ja criado;
- reutilizar o evento idempotentemente;
- concluir o mark `granted`.

## Gamification

O Live Settlement usa uma instancia dedicada de `GamificationService`
com o ruleset composto de settlement.

O ruleset global normal da Gamification nao e substituido.

## Reputacao

A 7D5 continua concedendo apenas XP.

Reputacao comunitaria permanece responsabilidade da Etapa 8.

## Feature flag

`MISSIONS_COMMUNITY_LIVE_REWARD_SETTLEMENT_ATIVO`

Default:

`OFF`

Valores aceitos para ativacao:

- `1`;
- `true`;
- `yes`;
- `on`.

Valor ausente ou desconhecido permanece fail-closed.

## Estado atual

A implementacao da 7D5 foi commitada em `93533dc`
(`feat: add live mission reward settlement`).

A ativacao controlada em producao foi concluida em 20/09/2026.

No ambiente real:

- `MISSIONS_COMMUNITY_LIVE_REWARD_SETTLEMENT_ATIVO=true`;
- o runtime real foi reciclado cirurgicamente;
- o supervisor foi preservado;
- Chrome/CDP permaneceu `HEALTHY`;
- a factory retornou `MissionCommunityLiveSettlementWiring`;
- o caminho live foi executado sobre uma descoberta ja aprovada.

## Validacao operacional

O canario idempotente confirmou:

- 0 eventos de missao novos;
- 3 eventos de missao idempotentes;
- 0 novas conclusoes de missao;
- 0 novos rewards;
- 0 rewards pendentes encontrados pelo settlement;
- 0 eventos de Gamification criados pelo canario;
- 0 XP duplicado;
- 0 rewards duplicados;
- reputacao comunitaria inalterada;
- SQLite integro;
- 0 erros de foreign key.

O estado antes e depois do canario permaneceu:

- 3 `mission_progress_events`;
- 3 `mission_progress`;
- 1 reward `granted`;
- 0 rewards `pending`;
- 1 evento `mission_reward_*`;
- 20 XP provenientes de reward de missao;
- 190 XP totais;
- 10 eventos totais de Gamification;
- reputacao 0.

## Fechamento

A 7D esta concluida.

O startup reconciliation permanece como mecanismo de recuperacao.
O Live Reward Settlement liquida novos rewards durante o fluxo
normal de aprovacao comunitaria, sem depender de restart.

A 7D continua concedendo apenas XP.
Community Reputation & Trust permanece responsabilidade da Etapa 8.

## Proximo passo

**7E - Missions Read API**

A 7E deve expor progresso, conclusao e rewards para leitura pelo cliente
sem permitir que o cliente escreva XP, reputacao ou estado das missoes.
