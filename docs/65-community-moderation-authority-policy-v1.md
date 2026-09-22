# Authoritative Moderation Policy & Service V1 - 8E3

## Status

8E3 CONCLUIDA E VALIDADA.

## Objetivo

A 8E3 cria a primeira camada realmente autoritativa de moderacao.

A 8E1 definiu que report e alegacao.

A 8E2 criou o ledger persistente de reports e decisions.

A 8E3 define quem pode produzir uma decision autoritativa.

## Fonte de autoridade

A V1 reutiliza a autoridade do control plane administrativo:

`RADAR_ADMIN_TOKEN`

O esquema e:

`Authorization: Bearer <token>`

A comparacao usa `hmac.compare_digest`.

## Fail closed

Moderacao e mais restritiva que uma operacao local comum.

Se `RADAR_ADMIN_TOKEN` nao estiver configurado, a autoridade de moderacao nao
existe.

Nao ha bypass de moderacao por loopback.

Nao sao autoridade:

- conta de usuario comum;
- sessao de usuario;
- reporter;
- volume de reports;
- reputacao;
- execucao local por si so.

## Principal auditado

A infraestrutura atual possui um token administrativo compartilhado.

Por isso a V1 nao afirma conhecer uma identidade humana individual.

O ator persistido e:

`radar-admin-control-plane-v1`

Origem:

`admin_control_plane`

Esse e um principal tecnico, nao uma pessoa.

Uma futura camada de identidades administrativas nomeadas pode substituir o
principal compartilhado sem alterar o ledger de reports.

## Ordem de autorizacao

A autorizacao acontece antes da consulta da denuncia.

Token ausente ou incorreto nao pode usar o service para descobrir se um report
existe.

## Policy de confirmed_abuse

A familia negativa nao vem do caller.

Ela e derivada server-side do motivo original do report:

- `spam` -> `spam_confirmado`;
- `fraud` -> `fraude_confirmada`;
- `malicious_link` -> `link_malicioso_confirmado`;
- `abuse` -> `abuso_confirmado`.

O caller nao informa `moderator_actor_id`.

O caller nao informa `familia_abuso_confirmado`.

## Motivos que nao podem virar confirmed_abuse na V1

- `off_topic`;
- `duplicate`;
- `other`.

Esses motivos ainda podem receber:

- `dismissed`;
- `keep_under_review`.

Isso evita converter categorias ambiguas em Trust negativo.

## Repository da 8E2

O repository continua deliberadamente nao autoritativo.

Ele garante:

- persistencia;
- idempotencia;
- state machine;
- invariantes de schema.

A decisao sobre autoridade pertence ao service da 8E3.

## Community Trust

A 8E3 ainda nao escreve Community Trust.

Uma `confirmed_abuse` autoritativa passa a ser uma entrada valida para a futura
Trust Bridge, mas nesta etapa:

- nenhuma evidence negative e criada;
- nenhuma evidence terminal e reclassificada;
- nenhum profile Trust e alterado.

## Runtime

A 8E3 ainda nao adiciona rota HTTP administrativa de moderacao.

Tambem nao ativa schema de moderacao no banco live.

Os testes usam somente:

- banco SQLite temporario;
- token administrativo explicitamente falso/de teste.

O token administrativo real nao e lido pelos testes.

## Validacao final da 8E3

A 8E3 foi validada sobre o baseline `05c8ac0`.

Resultados pre-closure:

- source audit aprovado;
- guard do control plane administrativo aprovado;
- pre-commit aprovado;
- 23 testes isolados da 8E3 aprovados;
- 43 testes acumulados da etapa 8E aprovados;
- 92 testes Trust + Moderation aprovados;
- testes fail-closed da authority aprovados;
- 7 testes da policy server-side de familias de abuso aprovados.

A autoridade V1 ficou definida como:

- fonte: `RADAR_ADMIN_TOKEN`;
- esquema: `Authorization: Bearer`;
- comparacao: `hmac.compare_digest`;
- ausencia de token: fail-closed;
- loopback bypass: inexistente;
- sessao de usuario final: sem autoridade;
- reporter: sem autoridade;
- volume de reports: sem autoridade.

O ator auditado e o principal tecnico:

`radar-admin-control-plane-v1`

A V1 nao afirma que esse principal identifica uma pessoa humana individual.

O service deriva server-side a familia de abuso confirmado e nao permite que o
caller informe `moderator_actor_id` ou `familia_abuso_confirmado`.

Motivos ambiguos (`off_topic`, `duplicate`, `other`) nao podem virar
`confirmed_abuse` na policy V1.

O banco live permaneceu read-only, com zero tabelas de Moderation, 2 evidencias
de Community Trust, 1 profile, `integrity_check=ok` e zero erros de foreign key.

A 8E3 ainda nao implementa Trust Bridge nem rota HTTP administrativa de
moderacao.

## Proximo passo

8E4 - Moderation Trust Bridge Core.
