# Moderation & Reporting Core Ledger V1 - 8E2

## Status

8E2 CONCLUIDA E VALIDADA.

## Objetivo

A 8E2 materializa o core persistente de Moderation & Reporting definido na
8E1.

Nesta etapa o repository e validado somente contra bancos SQLite temporarios.

O banco live nao recebe schema de moderacao ainda.

## Reports ledger

Tabela:

`community_moderation_reports`

Cada report preserva:

- id;
- chave de idempotencia;
- conta do reporter;
- target;
- motivo;
- detalhes;
- estado;
- timestamps.

O reporter referencia `contas_usuario.id`.

Na V1 o target referencia diretamente `community_discoveries.id`.

## Idempotencia de reports

A chave e produzida server-side:

`v1:community-report:<reporter>:<target_type>:<target_id>:<reason>`

O mesmo reporter nao cria duas denuncias iguais para o mesmo target e motivo.

Um retry semanticamente identico devolve a denuncia original.

Reutilizar a mesma identidade logica com detalhes diferentes falha fechado.

Reporters diferentes continuam podendo denunciar o mesmo target.

Motivos diferentes tambem permanecem auditaveis separadamente.

## Decision ledger

Tabela:

`community_moderation_decisions`

Decisions sao append-only.

Cada linha preserva:

- report;
- moderator actor;
- outcome;
- familia de abuso confirmada, quando aplicavel;
- justificativa;
- ocorrido_em;
- criado_em;
- chave de idempotencia da acao.

A chave segue:

`v1:community-moderation-decision:<report_id>:<action_key>`

## Autoridade do moderator

O repository armazena `moderator_actor_id`, mas nao concede autoridade.

Validar que aquele actor realmente e um moderador autorizado pertence a camada
server-side da 8E3.

Uma conta ativa comum nao ganha autoridade de moderacao por existir em
`contas_usuario`.

## Estados

Report nasce como:

`received`

`keep_under_review` move para:

`under_review`

`confirmed_abuse` e `dismissed` movem para:

`resolved`

Uma report resolvida rejeita nova decision.

Retry idempotente da propria decision ja persistida continua permitido mesmo
apos resolucao.

## Confirmed abuse

`confirmed_abuse` exige exatamente uma familia reconhecida:

- `abuso_confirmado`;
- `spam_confirmado`;
- `fraude_confirmada`;
- `link_malicioso_confirmado`.

Outcomes nao confirmatorios nao podem carregar familia de abuso.

## Relacao com Community Trust

A 8E2 nao escreve Community Trust.

Nenhuma denuncia altera Trust.

Nenhuma decision altera Trust nesta etapa.

O ledger terminal criado na 8D permanece imutavel.

Varios reports e ate varias decisions autoritativas podem existir para o mesmo
target por motivos de auditoria.

A futura Trust Bridge sera responsavel por converter abuso confirmado em no
maximo uma evidencia `negative` por discovery.

## Banco live

A 8E2 nao instancia o repository contra o banco live.

Todos os testes de schema e persistencia usam bancos temporarios.

O live e apenas auditado em modo read-only antes e depois.

## Fora da 8E2

Ainda nao existem nesta etapa:

- User-Facing Report API;
- Admin Moderation API;
- moderator authorization service;
- Trust Bridge;
- account suspension;
- content takedown;
- Gamification write;
- `reputacao_total` write.

## Validacao final da 8E2

A 8E2 foi validada sobre o baseline `45883a6`.

Resultados pre-closure:

- source audit semantico aprovado;
- `BEGIN IMMEDIATE` validado nos dois caminhos de escrita;
- pre-commit aprovado;
- 11 testes isolados da 8E2 aprovados;
- 19 testes acumulados da 8E1 + 8E2 aprovados;
- 68 testes Trust + Moderation aprovados;
- report idempotency validada;
- decision idempotency validada;
- decision state machine validada.

A auditoria SQLite temporaria confirmou:

- `integrity_check=ok`;
- zero erros de foreign key;
- 2 reports;
- 2 decisions;
- 1 report resolvido;
- 1 report recebido;
- 1 `confirmed_abuse`;
- 1 `keep_under_review`;
- zero chaves duplicadas de report;
- zero chaves duplicadas de decision;
- zero tabelas de Community Trust criadas.

O banco live permaneceu exclusivamente read-only:

- zero tabelas de Moderation;
- 2 evidencias de Community Trust;
- 1 profile de Community Trust;
- `integrity_check=ok`;
- zero erros de foreign key.

A 8E2 nao ativa moderator authority, Trust Bridge, API publica ou Admin API.

## Proximo passo

8E3 - Authoritative Moderation Policy & Service.
