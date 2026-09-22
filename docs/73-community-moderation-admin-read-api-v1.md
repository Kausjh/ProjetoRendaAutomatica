# Community Moderation Admin Read API V1 - 8E9A

## Status

8E9A CONCLUIDA E VALIDADA.

## Objetivo

Expor leitura administrativa de Community Moderation no control plane
existente sem abrir operacoes de escrita.

## Recovery

Duas tentativas iniciais de patch foram interrompidas por anchors textuais
fragilmente acoplados ao source atual.

A implementacao final usa a AST do Python para localizar semanticamente:

- `ServidorStatusAdministrativo.iniciar`;
- a classe interna `Handler`;
- `Handler.do_GET`;
- o guard `if token_administrativo`;
- o `try` principal das rotas GET;
- `runtime.main`;
- o assignment de `user_identity_service`.

O write repository de Community Moderation permanece intacto.

## Fronteira HTTP

A 8E9A usa `ServidorStatusAdministrativo`.

Autenticacao:

`Authorization: Bearer <RADAR_ADMIN_TOKEN>`

As rotas de Moderation falham fechado quando o token administrativo nao
esta configurado.

A User-Facing API nao participa desta etapa.

## Rotas

### GET /moderation/reports

Lista a fila pendente.

Parametros:

- `limite`: default 50, maximo 100;
- `offset`: default 0.

### GET /moderation/reports/{denuncia_id}

Retorna:

- denuncia;
- historico de decisions associado.

## Read projection

`CommunityModerationReadService` abre o SQLite diretamente com:

- URI `mode=ro`;
- `PRAGMA query_only = ON`;
- `PRAGMA foreign_keys = ON`.

A projection nao:

- inicializa schema;
- depende de `CommunityModerationRepository`;
- oferece qualquer metodo de escrita.

## Runtime

A instancia existente do `ServidorStatusAdministrativo` e reutilizada.

Depois que `user_identity_db` existe, o runtime cria a read projection e a
injeta na instancia administrativa antes de `servidor_status.iniciar()`.

Isso nao ativa persistentemente Community Moderation.

## Fronteiras preservadas

A 8E9A nao:

- cria report;
- registra decision;
- altera Trust;
- altera Gamification;
- habilita reconciliation automatica;
- habilita o runtime de Moderation persistentemente;
- implementa 8E9B;
- finaliza as semanticas 8E9C.

## Validacao final da 8E9A

A 8E9A foi validada sobre o baseline `02b2f23`.

Resultados pre-closure:

- 12 testes isolados aprovados;
- 124 testes acumulados de Moderation aprovados;
- 173 testes Trust + Moderation aprovados;
- source audit aprovado;
- pre-commit aprovado apos formatacao automatica.

Arquitetura validada:

- patch estrutural baseado em AST;
- write repository autoritativo inalterado;
- projection administrativa dedicada;
- SQLite aberto em `mode=ro`;
- `PRAGMA query_only = ON`;
- tentativa acidental de escrita bloqueada;
- control plane administrativo existente reutilizado;
- autenticacao por `RADAR_ADMIN_TOKEN`;
- fail-closed sem token administrativo;
- User-Facing API nao utilizada.

Rotas concluidas:

- `GET /moderation/reports`;
- `GET /moderation/reports/{denuncia_id}`.

Estado live final:

- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros de foreign key;
- nenhuma escrita da 8E9A.

Fronteiras preservadas:

- Decision Write API ainda nao existe;
- Public Report API ainda nao existe;
- runtime de Moderation nao foi habilitado persistentemente;
- reconciliation automatica continua desligada;
- runtime principal nao foi reiniciado.

## Proximo passo

8E9B - Authoritative Admin Decision API.
