# Community Moderation User Report Read-back V1 - 8E10C

## Status

8E10C CONCLUIDA E VALIDADA.

## Objetivo

Permitir que um usuario autenticado acompanhe apenas as denuncias que
ele proprio criou.

A 8E10C e deliberadamente limitada.

## Rotas

Lista:

`GET /api/v1/me/reports?limite=20&offset=0`

Detalhe:

`GET /api/v1/me/reports/{report_id}`

Ambas exigem `X-User-Session`.

A protecao de infraestrutura existente permanece preservada.

## Ownership

Toda leitura e filtrada por `reporter_conta_id` no repository.

Um usuario:

- pode listar apenas suas denuncias;
- pode abrir apenas suas denuncias;
- nao pode consultar denuncia de outra conta.

Uma denuncia inexistente e uma denuncia pertencente a outra conta
retornam o mesmo HTTP 404.

Isso evita usar o endpoint para enumerar reports de outros usuarios.

## Lista

A lista publica somente:

- `id`;
- `target_type`;
- `target_id`;
- `motivo`;
- `estado`;
- `criado_em`;
- `atualizado_em`.

`detalhes` nao aparece na lista.

Paginacao:

- limite default 20;
- limite maximo 100;
- offset default 0.

## Detalhe

O detalhe retorna os mesmos campos da lista e tambem os `detalhes`
originalmente enviados pelo proprio usuario.

## Campos internos que nao sao expostos

A User-Facing API nao retorna:

- `reporter_conta_id`;
- chave de idempotencia persistida;
- moderator actor;
- resultado administrativo;
- familia de abuso confirmado;
- justificativa do moderador;
- authority origin;
- dados internos de Trust.

A tabela de decisions nao e consultada pelo read-back publico.

O usuario acompanha somente o estado publico da denuncia:

- `received`;
- `under_review`;
- `resolved`.

## Persistencia

Nenhuma tabela, migration ou indice novo e necessario.

A 8E10C reutiliza o `CommunityModerationRepository` ja injetado pela
8E10A.

As novas operacoes de repository sao somente leitura.

## Fronteiras

A 8E10C nao:

- altera criacao de reports;
- altera a politica de idempotencia da 8E10B;
- cria decision;
- escreve Trust;
- adiciona UI no app;
- ativa feature flag;
- reinicia runtime;
- executa canario live;
- escreve no banco live.

A superficie visual permanece reservada para 8E11.

## Validacao final

A 8E10C foi validada sobre o baseline `c6de05a`.

Resultados pre-closure:

- pre-commit aprovado;
- 24 casos isolados da 8E10C aprovados;
- 69 casos Reporting 8E10A + 8E10B + 8E10C aprovados;
- 230 casos acumulados 8E1..8E10C aprovados;
- 49 casos Trust-only aprovados;
- 96 casos do servidor administrativo aprovados;
- 222 casos do servidor User-Facing aprovados.

A regressao acumulada sofreu uma ocorrencia ambiental
`WinError 10053` no Windows e passou integralmente no retry
automatico, sem alteracao de codigo.

Read-back concluido:

- lista somente reports do usuario autenticado;
- detalhe somente de report pertencente ao usuario autenticado;
- report alheio e report inexistente retornam o mesmo HTTP 404;
- ownership e filtrado no SQL do repository;
- detalhes nao aparecem na lista;
- detalhes enviados pelo proprio usuario aparecem no detalhe;
- reporter id nao e exposto;
- chave de idempotencia nao e exposta;
- moderator actor nao e exposto;
- resultado administrativo nao e exposto;
- justificativa interna nao e exposta;
- dados internos de Trust nao sao expostos;
- tabela de decisions nao e consultada pelo read-back publico.

Estado live:

- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros de foreign key;
- nenhuma escrita live;
- nenhuma alteracao de schema live.

A 8E10C nao altera criacao de reports nem a politica de idempotencia
da 8E10B e nao adiciona UI ao Public App.

## Proximo passo

8E11A - Public App Reporting Client / Read Model.
