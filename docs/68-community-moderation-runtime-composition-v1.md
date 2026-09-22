# Moderation Runtime Composition V1 - 8E6

## Status

8E6 CONCLUIDA E VALIDADA.

## Objetivo

A 8E6 cria um ponto unico de composicao para o runtime de Community
Moderation.

Ela conecta, em um unico objeto:

- `CommunityModerationRepository`;
- `CommunityDiscoveryRepository`;
- `CommunityTrustRepository`;
- `CommunityModerationAuthorityV1`;
- `CommunityModerationTrustBridge`;
- `CommunityModerationService`;
- `CommunityModerationTrustReconciliation`.

## Por que existe uma barreira de schema

Os repositories de Moderation, Community Discovery e Community Trust garantem
seus schemas durante a construcao.

Por isso a composicao nao pode ser chamada inadvertidamente contra o banco
live antes da etapa de ativacao controlada.

Existem duas barreiras.

Primeiro:

`COMMUNITY_MODERATION_RUNTIME_ATIVO`

O valor default documentado e `0`.

Segundo:

`permitir_schema_activation=False`

Mesmo que a flag seja ligada, nenhum repository e construido enquanto essa
permissao explicita continuar falsa.

## Ordem fail-closed

Quando a ativacao e realmente autorizada, a Authority e resolvida antes dos
repositories.

Se `RADAR_ADMIN_TOKEN` estiver ausente e nenhuma Authority explicita tiver sido
injetada, a composicao falha antes da inicializacao dos repositories.

Isso evita criar schema de Moderation apenas para descobrir depois que nao ha
autoridade administrativa disponivel.

## Trust Bridge

Quando a composicao e ativada com sucesso, o `CommunityModerationService`
recebe a Trust Bridge da 8E4.

Nao existe segundo caminho de escrita de Trust.

## Reconciliation

A reconciliation da 8E5 tambem e composta, mas nao roda automaticamente.

A flag e:

`COMMUNITY_MODERATION_RECONCILIATION_STARTUP_ATIVA`

Default:

`0`

Ela tambem pode ser controlada explicitamente pelo caller durante testes ou
uma futura ativacao operacional.

Se reconciliation for executada e retornar falhas, a ativacao e considerada
incompleta.

## Runtime principal

A 8E6 NAO altera `runtime.py`.

Portanto esta etapa ainda nao:

- cria Moderation schema no banco live;
- injeta a Moderation Service no processo principal;
- executa reconciliation no live;
- expoe Admin HTTP moderation routes;
- expoe User-Facing Report API.

## Testes

Todos os caminhos que criam schema ou escrevem dados utilizam SQLite
temporario.

O banco live e apenas auditado em `query_only`.

## Validacao final da 8E6

A 8E6 foi validada sobre o baseline `ddef57f`.

Resultados pre-closure:

- 10 testes isolados aprovados;
- 78 testes acumulados da Etapa 8 aprovados;
- 127 testes Trust + Moderation aprovados;
- 3 testes fail-closed aprovados;
- 5 testes de composition/reconciliation aprovados;
- pre-commit aprovado.

Invariantes confirmadas:

- runtime de Moderation desligado por default;
- schema activation exige permissao explicita;
- flag desligada nao instancia repositories;
- ausencia de permissao de schema nao instancia repositories;
- Authority e resolvida antes da construcao dos repositories;
- ausencia de Authority falha antes de schema;
- Trust Bridge e injetada no Moderation Service;
- nao existe segundo caminho de escrita de Trust;
- reconciliation service e composto;
- reconciliation startup permanece OFF por default;
- `runtime.py` principal nao foi alterado;
- nenhum processo principal foi ativado.

O banco live permaneceu read-only:

- `integrity_check=ok`;
- zero erros de foreign key;
- zero tabelas de Moderation;
- 2 evidencias Trust;
- 1 profile Trust;
- nenhuma escrita da 8E6.

A proxima etapa e a ativacao controlada somente do schema de Moderation.

## Proximo passo

8E7 - Moderation Live Schema Activation.
