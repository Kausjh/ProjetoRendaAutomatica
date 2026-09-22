# Moderation Trust Bridge Reconciliation V1 - 8E5

## Status

8E5 CONCLUIDA E VALIDADA.

## Objetivo

A 8E5 fecha o crash gap deliberado da 8E4.

Na 8E4 a decision autoritativa de Moderation e persistida antes da evidence
negative de Community Trust.

Se o processo falhar entre essas duas transacoes, a decision continua correta,
mas a evidence de Trust pode ficar ausente.

A reconciliation encontra esse estado e passa novamente pela mesma Trust
Bridge da 8E4.

## Sem segundo caminho de escrita

A reconciliation nao implementa uma escrita alternativa de Trust.

Ela reutiliza:

`CommunityModerationTrustBridge.processar_decisao(...)`

Portanto continuam valendo as mesmas validacoes de:

- ator autoritativo;
- motivo original do report;
- familia de abuso confirmada;
- target `community_discovery`;
- conta impactada server-side;
- chave canonica por discovery;
- no maximo um negative por discovery.

## Candidate selection

O repository ganha uma capacidade read-side:

`listar_decisoes_abuso_confirmado(...)`

Ela seleciona apenas:

- `resultado = confirmed_abuse`;
- `moderator_actor_id = radar-admin-control-plane-v1`.

A ordenacao e deterministica:

1. `ocorrido_em ASC`;
2. `id ASC`.

A leitura aceita `limit` e `offset`.

## Report correspondente

Cada decision reconciliada precisa possuir o report correspondente.

O report tambem precisa estar `resolved`.

Estado estrutural inconsistente nao e convertido silenciosamente em Trust.

Ele vira falha individual de reconciliation.

## Falhas por item

Uma decision corrompida ou inconsistente nao bloqueia necessariamente as demais.

O resultado da reconciliation informa:

- quantas decisions foram examinadas;
- quantas evidences foram criadas;
- quantas ja existiam;
- quais itens falharam.

## Idempotencia

Executar reconciliation repetidamente e seguro.

Se a evidence ja existir:

- nenhuma nova evidence e criada;
- o profile nao recebe novo negative;
- a bridge valida a semantica da evidence existente;
- o item conta como idempotente existente.

Multiplas decisions para a mesma discovery continuam produzindo no maximo um
negative.

## Autoridade

A reconciliation nao cria uma nova decision administrativa.

Por isso ela nao pede um novo Bearer token.

Ela opera somente sobre decisions que ja foram persistidas como autoritativas.

Mesmo assim, a Trust Bridge revalida:

- `moderator_actor_id`;
- familia de abuso;
- report reason.

## Evidence terminal

A evidence terminal da Community Discovery continua imutavel.

A reconciliation somente pode criar a evidence negative separada da Moderation.

## Runtime live

A 8E5 ainda nao:

- ativa schema de Moderation no live;
- injeta a bridge no runtime;
- agenda reconciliation;
- executa reconciliation contra o banco live.

Todos os writes dos testes usam SQLite temporario.

O live permanece apenas auditado em modo read-only.

## Validacao final da 8E5

A 8E5 foi validada sobre o baseline `f3b5d01`.

Resultados pre-closure:

- source audit aprovado;
- pre-commit aprovado;
- 11 testes isolados da 8E5 aprovados;
- 67 testes acumulados da etapa 8E aprovados;
- 116 testes Trust + Moderation aprovados;
- 6 testes criticos da reconciliation aprovados.

Invariantes validadas:

- somente `confirmed_abuse` do principal autoritativo entra como candidato;
- reconciliation reutiliza a Trust Bridge da 8E4;
- nao existe segundo caminho de escrita de Trust;
- ator persistido e revalidado;
- familia de abuso persistida e revalidada;
- nenhuma nova credencial administrativa e exigida;
- rerun da reconciliation e idempotente;
- varias execucoes nao empilham negatives;
- varias decisions para a mesma discovery nao empilham negatives;
- falha de um item nao bloqueia necessariamente os demais;
- evidence terminal permanece imutavel e sem reclassificacao.

A reconciliation ainda nao esta agendada nem ativada contra o banco live.

O banco live permaneceu read-only:

- `integrity_check=ok`;
- zero erros de foreign key;
- zero tabelas de Moderation;
- 2 evidencias Trust;
- 1 profile Trust;
- nenhuma escrita da 8E5.

## Proximo passo

8E6 - Moderation Runtime Composition.
