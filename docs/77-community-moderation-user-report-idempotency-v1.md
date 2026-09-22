# Community Moderation User Report Idempotency V1 - 8E10B

## Status

8E10B CONCLUIDA E VALIDADA.

## Objetivo

Fechar a politica publica de idempotencia e protecao contra denuncias
duplicadas do:

`POST /api/v1/me/reports`

## Idempotency-Key

A rota passa a exigir:

`Idempotency-Key: <opaque-key>`

Formato permitido:

- 1 a 128 caracteres;
- letras;
- numeros;
- ponto;
- underline;
- dois-pontos;
- hifen.

A chave e escopada pelo reporter autenticado.

O mesmo valor pode ser usado por contas diferentes sem colisao.

## Primeiro envio

Primeira chave valida + primeira denuncia semantica:

- persiste 1 report;
- HTTP 201;
- `criada=true`;
- `idempotent_replay=false`.

## Replay exato

Mesma conta + mesma Idempotency-Key + mesmo payload:

- nao cria outra linha;
- retorna o mesmo report;
- HTTP 200;
- `criada=false`;
- `idempotent_replay=true`.

## Reuso incorreto da chave

Mesma conta + mesma Idempotency-Key + payload diferente:

- nenhuma nova linha;
- HTTP 409;
- codigo `idempotency_key_reutilizada`.

## Duplicata semantica

A identidade semantica continua sendo:

- reporter;
- target type;
- target id;
- motivo.

Se uma chave diferente tenta criar novamente a mesma identidade
semantica:

- nenhuma segunda denuncia e criada;
- HTTP 409;
- codigo `denuncia_duplicada`.

Alterar apenas detalhes nao permite criar uma segunda denuncia para o
mesmo reporter, target e motivo.

## Persistencia

Nenhuma tabela nova e necessaria.

A 8E10B reutiliza:

- `community_moderation_reports.chave_idempotencia`;
- UNIQUE da chave;
- UNIQUE semantico ja existente;
- `BEGIN IMMEDIATE`.

O metodo legado `registrar_denuncia` e preservado.

A rota publica passa a usar `registrar_denuncia_usuario`.

## Fronteiras

A 8E10B nao:

- adiciona read-back;
- escreve Trust;
- cria decision;
- altera feature flag;
- executa restart;
- executa canario live;
- altera schema live.

Read-back permanece em 8E10C.

## Validacao final

A 8E10B foi validada sobre o baseline `ddf9e7e`.

Resultados pre-closure:

- auditoria estrutural AST aprovada;
- pre-commit aprovado;
- 18 casos isolados da 8E10B aprovados;
- 26 casos de regressao da 8E10A aprovados;
- 205 casos acumulados 8E1..8E10B aprovados;
- 254 casos Trust + Moderation + Reporting aprovados;
- 96 casos do servidor administrativo aprovados;
- 197 casos do servidor User-Facing aprovados.

Politica concluida:

- `Idempotency-Key` obrigatoria;
- chave escopada pelo reporter autenticado;
- primeira criacao retorna HTTP 201;
- replay exato retorna HTTP 200;
- mesma chave com payload diferente retorna HTTP 409;
- chave diferente para a mesma denuncia semantica retorna HTTP 409;
- a mesma chave pode existir para reporters diferentes;
- nenhuma tabela nova;
- nenhuma migration de schema;
- metodo legado `registrar_denuncia` preservado.

Estado live:

- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros de foreign key;
- nenhuma escrita live;
- nenhuma alteracao de schema live.

A 8E10B nao adiciona read-back, nao escreve Trust e nao cria decision.

O read-back limitado permanece reservado para 8E10C.

## Proximo passo

8E10C - Limited User Status / Read-back.
