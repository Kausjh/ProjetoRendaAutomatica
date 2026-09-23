# Authenticated Community Trust Profile API V1 - 8F2

## Status

8F2 CONCLUIDA E VALIDADA.

## Objetivo

A 8F2 abre a primeira superficie HTTP da Etapa 8F.

Endpoint:

`GET /api/v1/me/trust`

O endpoint retorna exclusivamente o perfil Community Trust
do usuario autenticado.

## Autenticacao

A rota reutiliza a infraestrutura User-Facing existente:

- `X-User-Session` e obrigatorio;
- a conta e resolvida server-side pela sessao;
- quando `API_APLICACAO_TOKEN` estiver configurado,
  o Bearer de infraestrutura continua obrigatorio.

A rota nao aceita identificador de conta em:

- path;
- query;
- body.

Isso elimina uma superficie desnecessaria de selecao horizontal
de sujeito.

## Response

A resposta continua limitada a:

- `evidencias_total`;
- `positivas_total`;
- `negativas_total`;
- `neutras_total`;
- `atualizado_em`;
- versao do read model;
- indicador de que score numerico nao esta definido.

Nao sao expostos:

- `conta_id`;
- evidence history;
- idempotency keys;
- origem/origem_id;
- metadata;
- policy internals;
- moderator actor;
- justificativas internas.

## Persistencia estritamente read-only

A 8F2 nao usa `CommunityTrustRepository` no runtime User-Facing.

Ela cria:

`CommunityTrustReadOnlyRepository`

Esse repository:

- abre SQLite com `mode=ro`;
- ativa `PRAGMA query_only = ON`;
- nao cria diretorios;
- nao executa `CREATE TABLE`;
- nao possui metodo de escrita;
- nao possui metodo de schema activation.

Banco ou tabela indisponivel resulta em fail closed HTTP 503.

## Lifecycle da conexao SQLite

A validacao inicial da 8F2 encontrou um problema real de lifecycle
especificamente observavel no Windows.

`sqlite3.Connection` usado diretamente como context manager controla
transacao, mas nao garante o fechamento do objeto da conexao ao sair
do bloco.

O repository read-only foi endurecido para usar:

`contextlib.closing(connection)`

Assim cada conexao SQLite:

- continua em `mode=ro`;
- continua com `PRAGMA query_only = ON`;
- e fechada explicitamente;
- nao deixa file handle residual apos leitura;
- nao depende de garbage collection para liberar o arquivo.

O teste nao recebeu retry nem workaround para esconder a falha.
O codigo de producao foi corrigido.

## Test fixture resource lifecycle

A segunda execucao de recovery confirmou que o fix do repository
estava correto e ativo.

A falha remanescente vinha do proprio setup do teste:

`with sqlite3.connect(database):`

Assim como no codigo de producao original, o context manager da
`sqlite3.Connection` controla transacao, mas nao fecha automaticamente
a conexao.

A fixture foi corrigida para:

1. abrir explicitamente a conexao de setup;
2. criar o arquivo SQLite vazio;
3. fechar explicitamente a conexao antes de exercitar o repository.

O teste continua exigindo que o arquivo possa ser removido no
`finally`.

Nao foi adicionado:

- retry de unlink;
- sleep para mascarar handle aberto;
- garbage collection forcado;
- relaxamento de assert;
- skip especifico para Windows.

Portanto a regressao continua cobrindo de fato o lifecycle do
repository read-only.

## Metodos

Somente GET e suportado para `/api/v1/me/trust`.

POST continua retornando HTTP 405.

## Cache

As respostas usam a fundacao HTTP existente e permanecem com:

`Cache-Control: no-store`

## AEGIS Security Impact Review

Esta etapa aumenta deliberadamente a superficie de ataque ao criar
um novo endpoint autenticado.

O aumento e reconhecido e limitado por:

- autenticação de infraestrutura existente quando configurada;
- sessao autenticada de usuario;
- sujeito derivado exclusivamente da sessao;
- ausencia de account selector;
- repository SQLite estritamente read-only;
- resposta minimizada;
- GET only;
- `Cache-Control: no-store`;
- fail closed.

A etapa nao introduz:

- endpoint anonimo;
- secret novo;
- dependencia nova;
- database novo;
- porta persistente nova;
- schema novo;
- write path novo.

Nenhuma protecao existente e silenciosamente enfraquecida.

## Fora de escopo

Continuam fora da 8F2:

- evidence history;
- Public App Trust client;
- Public App Trust UI.

Evidence history permanece reservado para a 8F3.

## Arvore 8F

- 8F1 - completed;
- 8F2 - Authenticated Trust Profile API;
- 8F3 - Trust Evidence History API;
- 8F4 - Public App Trust Client;
- 8F5 - Public App Trust Surface;
- 8F6 - Final Closure.

Nao existem subniveis escondidos.

## Validacao final

A 8F2 foi validada sobre o baseline `5775f6c`.

API:

- `GET /api/v1/me/trust`;
- `X-User-Session` obrigatorio;
- Bearer de infraestrutura preservado quando configurado;
- perfil exclusivamente self-only;
- sujeito derivado server-side da sessao;
- nenhum seletor de conta em path, query ou body;
- POST permanece nao permitido;
- `Cache-Control: no-store`.

Persistencia:

- `CommunityTrustReadOnlyRepository`;
- SQLite `mode=ro`;
- `PRAGMA query_only = ON`;
- nenhuma capacidade de schema activation;
- nenhum metodo de escrita;
- lifecycle de conexao explicitamente fechado com
  `contextlib.closing`.

Resource lifecycle:

- leak real do repository identificado e corrigido;
- leak independente da fixture de teste identificado e corrigido;
- nenhum retry de unlink;
- nenhum sleep para Windows;
- nenhum GC forcado;
- nenhuma assert relaxada;
- nenhuma falha mascarada.

Resultados pre-closure:

- 16 testes isolados 8F2 aprovados;
- 128 testes Community Trust aprovados;
- 239 testes Servidor API aprovados;
- 194 testes Community Moderation aprovados;
- 61 testes Public Mobile aprovados;
- 70 testes backend Reporting aprovados.

Live:

- `query_only` ativo;
- integrity check `ok`;
- zero foreign key errors;
- schema version 43;
- 0 moderation reports;
- 0 moderation decisions;
- 2 Trust evidence;
- 1 Trust profile;
- SHA-256 do banco inalterado;
- nenhuma escrita live;
- nenhuma alteracao de schema live.

## Security Impact Review - Protocolo AEGIS

A nova superficie HTTP autenticada foi explicitamente reconhecida.

As fronteiras validadas incluem:

- Zero Trust;
- Least Privilege;
- Defense in Depth;
- Data Minimization;
- Fail Closed;
- autenticacao de infraestrutura existente preservada;
- autenticacao User-Facing reutilizada;
- sujeito derivado exclusivamente da sessao;
- ausencia de seletor horizontal de conta;
- repository runtime estritamente read-only;
- response minimizada;
- `Cache-Control: no-store`;
- GET only.

Nao houve:

- endpoint anonimo novo;
- secret novo;
- database novo;
- dependencia nova;
- porta persistente nova;
- write path novo;
- enfraquecimento silencioso de seguranca.

## Proximo passo

8F3 - Trust Evidence History API.
