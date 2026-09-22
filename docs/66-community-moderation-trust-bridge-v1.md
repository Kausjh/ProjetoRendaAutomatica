# Moderation Trust Bridge Core V1 - 8E4

## Status

8E4 CONCLUIDA E VALIDADA.

## Objetivo

A 8E4 cria a primeira ponte entre uma decision autoritativa de Moderation e o
ledger de Community Trust.

Somente `confirmed_abuse` autoritativo pode gerar evidencia negativa.

## Evidencia separada

A Trust Bridge nao modifica a evidencia terminal criada pela 8D.

Ela cria uma nova evidencia:

- tipo: `community_moderation_confirmed_abuse`;
- classificacao: `negative`;
- origem: `community_moderation_v1`;
- impacto: `-1`.

A evidencia terminal anterior continua historicamente intacta.

## Conta impactada

O caller nao informa a conta que sera penalizada.

A conta e resolvida server-side a partir de:

`community_discovery.conta_id`

Isso impede que um cliente escolha arbitrariamente quem recebe Trust negativo.

## Authority

A bridge exige que a decision tenha sido atribuida ao principal:

`radar-admin-control-plane-v1`

Tambem exige que a familia de abuso persistida corresponda ao motivo original
do report segundo a policy server-side da 8E3.

## Idempotencia por discovery

A chave canonica e:

`v1:community-moderation:community-discovery:<discovery_id>:confirmed-abuse`

Report ID e decision ID nao fazem parte da chave.

Portanto:

- dez reports da mesma discovery nao geram dez penalidades;
- varias decisions confirmadas nao geram varias penalidades;
- retry da mesma decision nao duplica evidencia;
- corrida entre decisions diferentes nao duplica evidencia.

A primeira decision autoritativa que efetivamente cria a evidencia permanece
como `origin_id`.

## Concorrencia

A bridge faz um pre-check para o caminho comum.

A garantia final continua pertencendo ao `BEGIN IMMEDIATE` e a chave
idempotente do `CommunityTrustRepository`.

Se duas decisions diferentes passarem pelo pre-check ao mesmo tempo:

1. uma vence e cria a evidencia;
2. a outra encontra conflito semantico na mesma chave;
3. a bridge recarrega a evidencia vencedora;
4. valida sua semantica canonica;
5. retorna o resultado existente sem criar outro negative.

## Modelo transacional

A decision de Moderation e persistida primeiro.

A evidencia de Trust vem depois, em outra transacao.

Isso significa que falha na bridge:

- nao apaga a decision autoritativa;
- e propagada ao caller;
- pode ser reparada por retry idempotente.

Existe, portanto, um pequeno crash gap entre os dois ledgers.

A proxima etapa criara reconciliation para encontrar `confirmed_abuse`
autoritativo ainda sem evidencia negative correspondente.

## Service integration

`CommunityModerationService` passa a aceitar uma Trust Bridge opcional.

Sem bridge injetada, o comportamento anterior continua valido.

Com bridge injetada:

- `dismissed` nao escreve Trust;
- `keep_under_review` nao escreve Trust;
- `confirmed_abuse` chama a bridge depois da persistencia da decision.

## Banco live

A 8E4 nao injeta a bridge no runtime live.

Nao cria tabelas de Moderation no live.

Todos os testes com writes usam bancos SQLite temporarios.

O banco live continua apenas auditado em modo read-only.

## Fora da 8E4

Ainda nao fazem parte desta etapa:

- reconciliation da Trust Bridge;
- live schema activation de Moderation;
- live bridge injection;
- Admin HTTP moderation routes;
- User-Facing Report API;
- account suspension;
- content takedown;
- Gamification write;
- `reputacao_total` write.

## Validacao final da 8E4

A 8E4 foi validada sobre o baseline `cfc4776`.

Resultados pre-closure:

- 11 testes isolados da 8E4 aprovados;
- 55 testes acumulados da etapa 8E aprovados;
- 104 testes Trust + Moderation aprovados;
- `one-negative-per-discovery` validado;
- crash-gap + retry repair validado;
- evidence terminal da 8D permaneceu imutavel;
- defesas contra actor e family invalidos validadas.

Invariantes:

- somente `confirmed_abuse` autoritativo produz `negative`;
- conta impactada e resolvida server-side;
- impacto Trust igual a `-1`;
- no maximo um negative por discovery;
- reports e decisions adicionais nao empilham negatives;
- concorrencia nao empilha negatives;
- a primeira decision vencedora permanece como `origin_id`;
- evidence terminal nao e modificada nem reclassificada.

A decision de Moderation e commitada antes da Trust Bridge.

Falha posterior da bridge nao remove a decision.

Retry idempotente pode reparar o crash gap.

A 8E5 implementara reconciliation para esse gap.

O banco live permaneceu read-only, sem schema de Moderation e sem writes da 8E4.

## Proximo passo

8E5 - Moderation Trust Bridge Reconciliation.
