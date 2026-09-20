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

## Estado desta implementacao

O codigo da 7D5 pode ser commitado com a flag OFF.

A implementacao nao:

- altera o SQLite real;
- reinicia o runtime;
- habilita a feature em producao;
- altera o scraper manual do Mercado Livre;
- altera arquivos locais do Expo.

## Proximo passo

Executar ativacao controlada da 7D5 em producao e provar o caminho live
sem duplicacao de XP.
