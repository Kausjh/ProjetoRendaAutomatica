# Community Trust Core Ledger V1 - 8B

## Status

IMPLEMENTACAO CONCLUIDA; VALIDACAO DO SCHEMA REAL PENDENTE.

## Objetivo

Criar a persistencia autoritativa de Community Trust sem introduzir score,
peso numerico ou wiring de producao.

## Fonte de verdade

`community_trust_evidence` e o ledger append-only autoritativo.

Cada evidencia possui:

- conta;
- chave de idempotencia;
- tipo;
- classificacao;
- origem;
- identificador de origem;
- motivo opcional;
- versao de politica opcional;
- metadados;
- instante do evento;
- instante de persistencia.

## Classificacao

A camada core consegue armazenar:

- `positive`;
- `negative`;
- `neutral`.

Essas classificacoes nao possuem peso numerico na 8B.

A existencia de suporte a `negative` nao autoriza transformar qualquer
`rejected` em evidencia negativa. Essa decisao continua sujeita a politica
versionada posterior.

## Perfil materializado

`community_trust_profiles` mantem somente contagens:

- evidencias totais;
- positivas;
- negativas;
- neutras.

O perfil e uma projecao reconstruivel.

`CommunityTrustRepository.reconstruir_perfil(conta_id)` recalcula as contagens diretamente do ledger e substitui o snapshot materializado.

O ledger permanece a autoridade.

## Idempotencia

A chave e unica por conta.

Retry com a mesma chave e a mesma semantica retorna a evidencia existente sem
incrementar o perfil novamente.

Reuso da chave com semantica diferente falha fechado.

## Transacao

A evidencia e a atualizacao do perfil acontecem na mesma transacao com
`BEGIN IMMEDIATE`.

## Fronteiras

A 8B nao define:

- score;
- peso;
- thresholds;
- politica numerica;
- wiring com Community Discovery;
- escrita em `reputacao_total`;
- runtime;
- API publica;
- Public App;
- Offer Scoring;
- Price Intelligence.

## Validacao

Os testes desta fase usam bancos SQLite temporarios.

O banco real `database/user_identity.sqlite3` nao deve ser alterado antes da
validacao controlada posterior da 8B.

## Proximo passo

Inicializacao e validacao controlada do schema real da 8B.
