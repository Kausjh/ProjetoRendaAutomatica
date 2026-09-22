# Community Moderation Runtime Main Wiring V1 - 8E8A

## Status

8E8A CONCLUIDA E VALIDADA.

## Objetivo

Conectar a composition root de Community Moderation ao `runtime.py` sem
ativar a funcionalidade no ambiente real.

A 8E8A e somente wiring.

## Pre-requisito

A 8E7 esta concluida e o schema live de Moderation ja existe.

O live possui:

- `community_moderation_reports`;
- `community_moderation_decisions`;
- 0 reports;
- 0 decisions.

## Wiring

O `runtime.py` passa a importar:

- `ResultadoAtivacaoCommunityModeration`;
- `ativar_community_moderation_runtime`.

O helper
`_ativar_community_moderation_controlado(...)`
chama a composition root com:

- `permitir_schema_activation=True`;
- `executar_reconciliation=False`.

A permissao de schema so e aceitavel porque a 8E7 ativou e validou
previamente o schema live.

Com a feature flag OFF, a composition root retorna antes de construir
repositories.

## Reconciliation

A 8E8A bloqueia explicitamente reconciliation no startup principal.

Mesmo que a flag
`COMMUNITY_MODERATION_RECONCILIATION_STARTUP_ATIVA`
seja configurada acidentalmente, o wiring principal passa
`executar_reconciliation=False`.

Reconciliation controlada pertence a 8E8C.

## O que esta etapa nao faz

A 8E8A nao:

- reinicia o runtime;
- liga `COMMUNITY_MODERATION_RUNTIME_ATIVO`;
- cria reports;
- cria decisions;
- executa reconciliation;
- expoe Moderation Service para HTTP;
- cria Admin HTTP API;
- cria User Reporting API;
- altera Trust;
- altera Gamification.

## Validacao final da 8E8A

A 8E8A foi validada sobre o baseline `43bc0bc`.

Resultados pre-closure:

- 8 testes isolados aprovados;
- 93 testes acumulados de Moderation aprovados;
- 142 testes Trust + Moderation aprovados;
- source audit aprovado;
- pre-commit aprovado.

Invariantes confirmadas:

- o `runtime.py` possui exatamente uma chamada controlada;
- a feature flag de Community Moderation permanece OFF por default;
- a feature flag real permaneceu OFF;
- o schema ja estava ativo pela 8E7;
- `permitir_schema_activation=True` somente reutiliza o schema existente;
- `executar_reconciliation=False` bloqueia explicitamente reconciliation;
- a flag de reconciliation do ambiente nao pode disparar reconciliation pelo main;
- o runtime principal nao foi reiniciado;
- Trust Bridge nao foi ativada live;
- reconciliation nao foi executada live;
- Admin HTTP nao foi integrado;
- User Reporting API nao foi integrada.

O banco live permaneceu somente leitura durante a 8E8A:

- 2 tabelas de Moderation;
- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- nenhuma escrita da 8E8A.

## Proximo passo

8E8B - Controlled Live Bridge Activation.
