# Moderation & Reporting Model V1 - 8E1

## Status

8E1 CONCLUIDA E VALIDADA.

## Objetivo

A 8E1 define a autoridade, as entidades e as fronteiras da camada de
Moderation & Reporting antes de qualquer schema ou escrita no banco live.

A regra principal e:

**denuncia e alegacao; decisao de moderacao e autoridade.**

Quantidade de denuncias, reputacao do denunciante ou qualquer threshold
automatico nao confirmam abuso por conta propria.

## Target da V1

A V1 de moderacao atua somente sobre:

`community_discovery`

O target e identificado por `community_discoveries.id`.

Targets sociais futuros, como comentarios, ficam reservados para etapas
posteriores.

## Identidade do denunciante

O denunciante precisa ser uma conta autenticada.

A identidade deve ser atribuida server-side a partir de `contas_usuario.id`.

O cliente nao pode informar arbitrariamente:

- a conta impactada;
- a identidade do moderador;
- uma classificacao de Trust.

## Motivos de denuncia

A V1 reconhece:

- `spam`;
- `fraud`;
- `malicious_link`;
- `abuse`;
- `off_topic`;
- `duplicate`;
- `other`.

Uma denuncia criada nao altera Community Trust.

## Estados da denuncia

- `received`;
- `under_review`;
- `resolved`.

O estado inicial e `received`.

## Decisao de moderacao

Resultados previstos:

- `confirmed_abuse`;
- `dismissed`;
- `keep_under_review`.

Somente `confirmed_abuse`, produzido por autoridade server-side confiavel,
pode futuramente autorizar uma evidencia negativa de Community Trust.

## Familias autoritativas de abuso

A camada de moderacao preserva as familias ja reconhecidas pela policy:

- `abuso_confirmado`;
- `spam_confirmado`;
- `fraude_confirmada`;
- `link_malicioso_confirmado`.

Mapeamento inicial:

- `abuse` -> `abuso_confirmado`;
- `spam` -> `spam_confirmado`;
- `fraud` -> `fraude_confirmada`;
- `malicious_link` -> `link_malicioso_confirmado`.

`off_topic`, `duplicate` e `other` nao geram automaticamente Trust negativo.

## Separacao entre denuncia e Trust

A 8D ja grava uma evidencia terminal da discovery com chave:

`v1:community-discovery:<discovery_id>`

Essa evidencia e historica e nao deve ser reescrita ou reclassificada por uma
moderacao posterior.

Quando a ponte de moderacao for implementada, abuso confirmado criara uma
evidencia adicional:

- tipo: `community_moderation_confirmed_abuse`;
- classificacao: `negative`;
- origem: `community_moderation_v1`;
- `origem_id`: id da decisao autoritativa;
- conta impactada: contribuidor da discovery, resolvido server-side.

A chave de idempotencia prevista e:

`v1:community-moderation:community-discovery:<discovery_id>:confirmed-abuse`

Isso garante no maximo uma evidencia negativa de moderacao por discovery,
independentemente de quantas pessoas denunciem o mesmo target.

## Anti-manipulacao

Nao sao autoridades:

- volume de denuncias;
- reputacao do denunciante;
- self-report;
- escolha do cliente;
- simples rejeicao tecnica da discovery.

Multiplicar reports nao multiplica penalidades.

## Auditabilidade

A futura persistencia precisa preservar:

- reporter;
- target;
- motivo original;
- moderator actor;
- resultado;
- familia de abuso confirmada;
- timestamp da decisao.

Decisoes devem ser auditaveis e nao devem apagar a evidencia terminal
historica da 8D.

## Boundaries da 8E1

A 8E1 nao:

- altera schema SQLite;
- escreve no banco live;
- cria endpoint publico de denuncia;
- cria admin API;
- suspende conta;
- remove conteudo;
- escreve em Gamification;
- escreve em `reputacao_total`;
- influencia Offer Scoring;
- influencia Price Intelligence;
- grava evidencia negativa.

## Validacao final da 8E1

A 8E1 foi validada sobre o baseline `371646d`.

Resultados pre-closure:

- pre-commit aprovado;
- 7 testes isolados aprovados;
- 56 testes da regressao Trust + 8E1 aprovados;
- contract assert aprovado;
- banco live auditado em modo read-only;
- `integrity_check=ok`;
- zero erros de foreign key;
- zero tabelas de Moderation/Reporting no live;
- nenhuma escrita no banco live.

Decisoes arquiteturais validadas:

- report e alegacao, nao autoridade;
- quantidade de reports nao confirma abuso;
- confirmacao exige autoridade server-side confiavel;
- evidencia terminal da 8D nao e reescrita;
- eventual evidencia negativa de moderacao sera separada e aditiva;
- no maximo uma evidencia negativa de moderacao por discovery;
- nenhuma escrita em Gamification ou `reputacao_total`.

## Proximo passo

8E2 - Moderation & Reporting Core Ledger.
