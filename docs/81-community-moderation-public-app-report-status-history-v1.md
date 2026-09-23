# Community Moderation Public App Report Status / History V1 - 8E11C

## Status

8E11C CONCLUIDA E VALIDADA.

## Objetivo

Concluir a superficie Public App da 8E11 com historico e
acompanhamento das denuncias pertencentes ao usuario autenticado.

A 8E11C reutiliza integralmente os endpoints e hooks entregues na
8E10C e 8E11A.

## Entrada

A tela `/account` recebe uma nova opcao:

`Minhas denúncias`

Ela abre:

`/reports`

## Historico

A tela `/reports` usa:

`useCommunityReports`

Configuracao inicial:

- limit 100;
- offset 0;
- pull-to-refresh;
- estado vazio;
- erro com retry.

O backend continua sendo responsavel por restringir a lista ao
usuario autenticado.

## Detalhe

Cada item do historico abre:

`/report-status`

Parametro:

`reportId`

A tela usa:

`useCommunityReport`

e mostra somente os campos publicos previamente definidos:

- id;
- target;
- motivo;
- status;
- data de criacao;
- ultima atualizacao;
- detalhes originalmente enviados pelo usuario.

## Status

Os tres estados publicos sao:

- received -> Recebida;
- under_review -> Em análise;
- resolved -> Concluída.

`resolved` representa encerramento do workflow de revisao.

A interface nao interpreta esse estado como confirmacao de abuso,
fraude ou qualquer outra violacao.

## Privacidade

A UI nao exibe:

- reporter_conta_id;
- chave de idempotencia persistida;
- moderator actor;
- resultado administrativo;
- justificativa interna;
- authority origin;
- dados internos de Trust.

## Read-only

A 8E11C nao:

- altera criacao de reports;
- altera a UI de submissao da 8E11B;
- altera backend;
- altera banco;
- altera schema;
- ativa runtime;
- reinicia servidor;
- executa canario live;
- grava no banco live.

## Fechamento da 8E11

Quando a 8E11C for validada e commitada:

- 8E11A estara concluida;
- 8E11B estara concluida;
- 8E11C estara concluida;
- a superficie Public App de reporting da 8E11 estara completa.

## Validacao final

A 8E11C foi validada sobre o baseline `1b8d54e`.

Resultados pre-closure:

- auditoria estrutural aprovada;
- pre-commit aprovado;
- typecheck do Public App aprovado;
- 12 testes isolados da 8E11C aprovados;
- 60 testes da regressao Public Mobile aprovados;
- 70 testes do backend Reporting aprovados.

A superficie concluida possui:

- entrada `Minhas denúncias` em `/account`;
- historico em `/reports`;
- detalhe e acompanhamento em `/report-status`;
- `useCommunityReports` para lista;
- `useCommunityReport` para detalhe;
- limite inicial de 100 reports;
- pull-to-refresh;
- estados Recebida, Em análise e Concluída;
- exibicao dos detalhes originalmente enviados pelo usuario.

A UI nao interpreta `resolved` como confirmacao de abuso.

A UI nao exibe dados internos de moderacao, identidade interna do
reporter, chave persistida de idempotencia, moderator actor,
resultado administrativo, justificativa interna ou dados de Trust.

Estado live:

- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros de foreign key;
- nenhuma escrita live;
- nenhuma alteracao de schema live.

Com este fechamento:

- 8E11A concluida;
- 8E11B concluida;
- 8E11C concluida;
- 8E11 Public App Reporting Surface concluida.

## Proximo passo

8E12A - Operational Closure.
