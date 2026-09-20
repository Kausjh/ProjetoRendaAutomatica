# Missions & Community Rewards V1 - Settlement Core 7D1

## Status

7D1 implementada localmente.

Nao ha runtime wiring, settlement no banco real, API publica ou alteracao
do Public App nesta subetapa.

## Problema

O Mission Engine possui grants `pending`.

O Gamification Engine possui um ledger idempotente de eventos e um perfil
materializado.

Os dois repositories usam o mesmo arquivo SQLite, mas cada repository
controla sua propria conexao e sua propria transacao.

Reescrever os dois repositories para compartilhar uma transacao aumentaria
a superficie de risco da Etapa 7 sem necessidade.

## Estrategia

A 7D1 usa `recoverable-two-step`.

Ordem:

1. registrar o evento de XP no ledger de gamification;
2. marcar o reward grant como `granted`, usando o ID do evento como
   `referencia_concessao`.

A chave de idempotencia do evento e derivada exclusivamente do ID do grant:

`v1:mission-reward-settlement:{reward_grant_id}`

## Janela de falha

Existe uma janela deliberada entre as duas transacoes.

Se o processo morrer depois da gravacao do evento de XP e antes de marcar
o reward como `granted`, o grant permanece `pending`.

No retry:

- a mesma chave encontra o evento ja persistido;
- nenhum XP adicional e criado;
- o mesmo event ID e usado como referencia;
- o grant e finalmente marcado como `granted`.

Portanto a janela e recuperavel e nao produz XP duplicado.

## Regras de XP

A 7D1 nao altera `services/gamification_production_rules.py`.

Ela cria um ruleset composto somente para settlement:

- preserva as cinco regras existentes;
- preserva os thresholds de nivel;
- adiciona `mission_reward_community_primeira_aprovada` = 20 XP;
- adiciona `mission_reward_community_cinco_aprovadas` = 50 XP;
- adiciona `mission_reward_community_dez_aprovadas` = 100 XP;
- todas as regras de reward possuem reputacao 0.

A versao auditavel e:

`gamification-reputation-production-v1+missions-community-rewards-settlement-v1`

## Validacoes fail-closed

O settlement rejeita reward quando:

- o status nao e `pending`;
- o tipo nao e `xp`;
- o ruleset da missao diverge;
- a instancia diverge;
- a quantidade de XP diverge da politica;
- a chave de gamification ja existe com semantica diferente;
- o grant ja foi concedido com outra referencia.

## Fronteiras

A 7D1 nao implementa:

- runtime settlement;
- mutacao do banco real;
- reputacao comunitaria;
- contributor trust;
- ranking;
- comentarios;
- API de missoes;
- UI de missoes;
- alteracao de offer scoring;
- alteracao de Price Intelligence.

## Proximo passo

7D2 - Runtime Settlement Reconciliation.

A 7D2 deve executar o settlement depois da reconciliacao das missoes e
antes de disponibilizar o estado final de gamification para o restante do
runtime, ainda com ativacao real controlada em uma etapa separada.
