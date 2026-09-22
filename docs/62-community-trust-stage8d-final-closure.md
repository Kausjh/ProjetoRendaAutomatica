# Community Reputation & Trust V1 - Etapa 8D Final Closure

## Status

8D CONCLUIDA E VALIDADA.

## Escopo concluido

A etapa 8D encerra o wiring operacional do Community Trust entre Community
Discovery, policy, ledger, reconciliacao historica e runtime real.

Foram concluidos:

- 8D1 - decisao atomica + escrita no ledger;
- 8D2 - terminal hook para `approved` e `rejected`;
- 8D3 - reconciliacao historica deterministica e idempotente;
- 8D3B - backfill controlado do banco live;
- 8D4A - ativacao do terminal hook no Community Discovery runtime real.

## Garantias operacionais

O fluxo terminal agora:

1. persiste a Community Discovery terminal;
2. executa o Community Trust Terminal Hook;
3. recarrega a discovery autoritativa;
4. aplica a policy;
5. conta positives na janela dentro da transacao autoritativa;
6. grava evidence + atualiza profile atomicamente.

A reconciliacao continua como mecanismo de reparo caso o hook live falhe.

## Idempotencia

A chave permanece:

`v1:community-discovery:<discovery_id>`

Uma discovery terminal nao pode produzir duas evidencias para a mesma conta.

## Backfill historico

O backfill controlado da 8D3B:

- processou 2 candidatos;
- criou 2 evidencias;
- teve 0 falhas;
- classificou o rejected fora do nicho como `neutral`;
- classificou o approved de pipeline como `positive`;
- provou segunda execucao no-op;
- preservou o backup pre-mutacao.

## Estado live no fechamento

- terminal discoveries: 2;
- evidencias: 2;
- profiles: 1;
- positive: 1;
- negative: 0;
- neutral: 1;
- candidatos sem evidence: 0;
- terminais cobertos: 2;
- chaves idempotentes duplicadas: 0;
- origins orfas: 0;
- divergencias profile/ledger: 0;
- integrity check: `ok`;
- erros de foreign key: 0.

## Runtime real

O `CommunityDiscoveryScraper` injeta o Community Trust Terminal Hook quando
constroi automaticamente sua queue.

O approval hook de Missions permanece independente.

Falha de composicao do Trust continua fail-open e a reconciliacao permanece
como caminho de recuperacao.

## Boundaries preservadas

A 8D nao introduziu:

- autoridade de moderacao;
- autoridade de abuso confirmado;
- escrita em Gamification;
- escrita em `reputacao_total`;
- mudanca na API publica;
- mudanca no app publico.

Essas fronteiras permanecem fora da 8D.

## Proximo passo

8E - Moderation & Reporting Foundation.
