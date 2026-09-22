# Community Trust Terminal Hook V1 - 8D2

## Status

8D2 CONCLUIDA E VALIDADA.

## Objetivo

Conectar a transicao terminal da Community Discovery ao Community Trust
sem substituir ou acoplar o hook existente de Missions.

## Fluxo

A descoberta e persistida primeiro como `approved` ou `rejected`.

Depois da persistencia, a queue executa o Terminal Community Trust Hook.

O hook recarrega a descoberta pelo repository e valida:

- `descoberta_id`;
- `conta_id`;
- status terminal;
- `ocorrido_em`.

Somente depois dessas validacoes ele chama o
`CommunityTrustDiscoveryWiring` introduzido na 8D1.

## Approved

`approved` continua executando o `approval_hook` existente de Missions.

Depois, de forma independente, executa o `terminal_hook` de Community Trust.

Falha em um hook nao impede a tentativa do outro.

## Rejected

Rejeicao direta executa o terminal hook depois de persistida.

Rejeicao terminal causada por erro de processamento tambem executa o terminal
hook depois de persistida.

Um erro transitorio que produz `retry` nao executa o terminal hook.

## Eventual consistency

A descoberta terminal nao e revertida se o Trust falhar.

Isso e intencional.

A evidencia possui idempotencia por descoberta e a 8D3 adicionara a
reconciliacao historica/operacional capaz de recuperar terminais sem evidencia.

## Autoridade de abuso

A 8D2 nao cria fonte autoritativa de abuso.

Por isso um `rejected` continua seguindo a Production Trust Policy com
`abuso_confirmado_autoritativamente=False`.

Moderacao e autoridade permanecem reservadas para a 8E.

## Boundaries

A 8D2 nao ativa:

- composicao runtime live;
- backfill historico;
- reconciliacao historica;
- Gamification;
- `reputacao_total`;
- API publica;
- app publico;
- moderacao.

## Validacao final da 8D2

A 8D2 foi validada sobre o baseline `a755396`.

Resultados pre-closure:

- pre-commit aprovado;
- 9 testes isolados da 8D2 aprovados;
- 5 testes originais da Community Discovery Queue aprovados;
- 87 testes acumulados de Queue + Community Trust aprovados;
- `approved` gerando evidencia positiva validado;
- `rejected` direto gerando evidencia neutra validado;
- rejeicao terminal por erro gerando evidencia validada;
- `retry` sem Community Trust validado;
- hook de Missions preservado;
- hooks de Missions e Community Trust independentes;
- falha do Trust sem rollback da descoberta validada;
- idempotencia do terminal hook validada;
- identidade divergente em fail-closed validada;
- boundaries do contrato aprovadas;
- nenhum runtime composition live ativado;
- nenhuma reconciliacao historica executada;
- nenhum backfill live executado;
- nenhuma escrita em Gamification ou `reputacao_total`.

A Community Discovery continua sendo a fonte autoritativa do estado terminal.
O Community Trust opera apos a persistencia do terminal e pode ser recuperado
pela reconciliacao da 8D3 caso o hook falhe.

## Proximo passo

8D3 - Community Trust Reconciliation & Backfill.
