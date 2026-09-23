# Community Moderation Operational Readiness V1 - 8E12A

## Status

8E12A CONCLUIDA E VALIDADA.

## Objetivo

A 8E12A inicia o fechamento operacional da Community Moderation.

Ela adiciona um preflight executavel, deterministico e read-only para
responder se o ambiente esta seguro em standby ou preparado para uma
ativacao controlada posterior.

A 8E12A nao ativa nada.

## Comando

Standby:

`python scripts/community_moderation_operational_preflight.py --mode standby`

Preparacao para ativacao:

`python scripts/community_moderation_operational_preflight.py --mode activation`

O modo `activation` apenas valida pre-condicoes.

Ele nao liga o runtime.

## Banco

O preflight abre:

`database/user_identity.sqlite3`

somente com SQLite `mode=ro`.

Tambem aplica:

`PRAGMA query_only = ON`

e verifica:

- `PRAGMA integrity_check`;
- `PRAGMA foreign_key_check`;
- existencia das tabelas operacionais obrigatorias.

## Tabelas obrigatorias

- `community_moderation_reports`;
- `community_moderation_decisions`;
- `community_trust_evidence`;
- `community_trust_profiles`.

Contagens podem ser exibidas para observabilidade.

Nenhuma contagem precisa permanecer zero para que o sistema seja
considerado saudavel.

## Contracts terminais

O preflight verifica contracts concluidos para os gates:

- 8E9C;
- 8E10C;
- 8E11C.

Isso cobre o control plane administrativo, o read-back autenticado e
a superficie Public App final.

## Runtime wiring

O preflight verifica estruturalmente que `runtime.py` ainda contem:

- ativacao controlada de Community Moderation;
- autorizacao explicita de schema;
- reconciliacao automatica desabilitada no wiring principal;
- wiring do decision service;
- wiring do repository user-facing.

## Standby

O modo `standby` exige:

- `COMMUNITY_MODERATION_RUNTIME_ATIVO` OFF;
- `COMMUNITY_MODERATION_RECONCILIATION_STARTUP_ATIVA` OFF.

`RADAR_ADMIN_TOKEN` nao e requisito para um standby seguro.

## Activation readiness

O modo `activation` exige:

- runtime flag ON;
- startup reconciliation OFF;
- `RADAR_ADMIN_TOKEN` configurado.

O valor do token nunca e impresso.

O preflight informa somente se existe configuracao utilizavel.

## Fail closed

Qualquer gate operacional ausente entra em `blockers` e produz exit
code diferente de zero.

## Limites da 8E12A

Esta etapa nao:

- altera runtime;
- ativa feature flag;
- executa reconciliation;
- chama API administrativa;
- chama User-Facing API;
- executa canario;
- escreve no banco;
- altera schema;
- reinicia processo.

## Arvore 8E12

A arvore permanece somente:

- 8E12A - Operational Readiness / Preflight;
- 8E12B - Controlled Operational Canary;
- 8E12C - Final Operational Closure.

Nao existem subniveis escondidos.

## Validacao final

A 8E12A foi validada sobre o baseline `3e66ed1`.

O preflight real de standby retornou `ready=true` e zero blockers.

Validacoes operacionais:

- banco aberto em modo read-only;
- `PRAGMA query_only = ON`;
- `integrity_check=ok`;
- 0 erros de foreign key;
- tabelas operacionais obrigatorias presentes;
- contract terminal 8E9C concluido;
- contract terminal 8E10C concluido;
- contract terminal 8E11C concluido;
- runtime wiring completo;
- token administrativo detectado sem exposicao do valor.

Estado live observado:

- 0 moderation reports;
- 0 moderation decisions;
- 2 Trust evidence;
- 1 Trust profile.

Resultados pre-closure:

- 10 testes isolados da 8E12A aprovados;
- 171 testes Community Moderation aprovados;
- 61 testes Public Mobile aprovados;
- 70 testes backend Reporting aprovados.

Tambem foram validados:

- precedencia explicita de process environment sobre `.env`;
- valor vazio explicito no process environment mascara fallback do `.env`;
- teste de token administrativo hermetico;
- JSON temporario UTF-8 sem BOM.

A 8E12A nao:

- ativou runtime;
- executou reconciliacao;
- chamou API administrativa;
- chamou User-Facing API;
- executou canario live;
- escreveu no banco live;
- alterou schema live.

A arvore operacional continua exatamente:

- 8E12A - Operational Readiness / Preflight;
- 8E12B - Controlled Operational Canary;
- 8E12C - Final Operational Closure.

## Proximo passo

8E12B - Controlled Operational Canary.
