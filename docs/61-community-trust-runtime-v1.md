# Community Trust Runtime V1 - 8D4A

## Status

8D4A CONCLUIDA E VALIDADA.

## Motivo

A 8D1 implementou a decisao atomica e o ledger.

A 8D2 implementou o Terminal Community Trust Hook.

A 8D3 implementou reconciliacao, realizou o backfill historico controlado e
deixou zero terminal discoveries sem evidencia.

Ainda faltava conectar o terminal hook ao construtor real usado pelo
`CommunityDiscoveryScraper`.

Sem essa composicao, discoveries futuras dependeriam de reconciliacao posterior
em vez de produzirem Trust imediatamente apos a transicao terminal.

## Composicao

Quando `CommunityDiscoveryScraper` cria sua propria queue:

1. cria `CommunityDiscoveryRepository`;
2. cria o Terminal Community Trust Hook live;
3. preserva separadamente o `approval_hook` de Missions;
4. injeta ambos na `CommunityDiscoveryQueueService`.

O Trust hook continua independente do hook de Missions.

## Failure mode

Se a composicao do Community Trust falhar durante a inicializacao, o worker
continua fail-open.

A discovery pode continuar sendo processada e a reconciliacao da 8D3 permanece
como caminho de reparo eventual.

Falha de Trust nao transforma a discovery em erro de pipeline.

## Queue explicitamente injetada

Se um caller fornece `queue_service` explicitamente ao scraper, o objeto
fornecido continua sendo usado sem substituicao.

Isso preserva testes, callers especializados e composicoes externas.

## Estado historico antes da ativacao

O backfill 8D3B concluiu com:

- 2 terminal discoveries;
- 2 evidencias de Community Trust;
- 1 profile;
- 1 `positive`;
- 0 `negative`;
- 1 `neutral`;
- zero candidatos restantes;
- segunda execucao no-op;
- `integrity_check=ok`;
- zero erros de foreign key.

## Boundaries

A 8D4A nao:

- cria discovery sintetica no banco live;
- reexecuta o backfill live;
- cria autoridade de moderacao;
- escreve em Gamification;
- escreve em `reputacao_total`;
- altera API publica;
- altera app publico.

## Validacao final da 8D4A

A 8D4A foi validada sobre o baseline `114dcac`.

Resultados pre-closure:

- pre-commit aprovado;
- 6 testes isolados de runtime aprovados;
- 7 testes do Community Discovery Scraper aprovados;
- 5 testes da Community Discovery Queue aprovados;
- 109 testes acumulados da etapa 8D aprovados;
- composicao real do terminal hook validada;
- `approved` gerando evidencia `positive` no runtime validado;
- `rejected` gerando evidencia `neutral` no runtime validado;
- failure mode de composicao fail-open validado;
- hook de Missions preservado e separado do Trust;
- reconciliacao mantida como caminho de reparo;
- banco live preservado em modo read-only durante a 8D4A.

Estado live observado apos o backfill historico:

- 2 terminal discoveries;
- 2 evidencias de Community Trust;
- 1 profile;
- 1 evidencia `positive`;
- 0 evidencias `negative`;
- 1 evidencia `neutral`;
- zero candidatos restantes;
- `integrity_check=ok`;
- zero erros de foreign key.

A 8D4A nao criou discovery sintetica live e nao reexecutou o backfill.

## Proximo passo

8D4B - Final Validation & Closure.
