# Community Trust Wiring & Reconciliation V1 - 8D

## Status

8D1 CONCLUIDA E VALIDADA.

## Objetivo da 8D1

Fechar a fronteira transacional entre a Production Trust Policy V1 e o
Community Trust Evidence Ledger.

A decisao de classificacao nao pode confiar em uma contagem fornecida pelo
caller.

## Transacao atomica

`CommunityTrustRepository.registrar_evidencia_com_decisao_atomica` executa sob
`BEGIN IMMEDIATE`:

1. verifica idempotencia;
2. recupera a contagem positiva autoritativa da janela;
3. executa a Production Trust Policy;
4. persiste a evidencia;
5. atualiza o perfil materializado;
6. realiza commit.

A contagem e a escrita ficam protegidas pela mesma transacao.

## Janela positiva

A V1 usa:

- limite: 10;
- janela: 86400 segundos;
- escopo: conta;
- fonte: `community_trust_evidence`;
- classificacao contada: `positive`;
- tempo autoritativo: `ocorrido_em`.

`positive_count_before` e persistido nos metadados da evidencia para preservar
a semantica original em retries idempotentes.

## Rejected

A 8D1 nao transforma `rejected` em evidencia negativa automaticamente.

Sem uma fonte autoritativa de abuso confirmado, a policy recebe
`abuso_confirmado_autoritativamente=False`.

Moderacao e confirmacao autoritativa continuam reservadas para a 8E.

## Fronteiras

A 8D1 nao ativa:

- hook terminal da Community Discovery;
- reconciliacao historica;
- backfill live;
- runtime;
- Gamification;
- `reputacao_total`;
- API publica;
- app publico;
- moderacao;
- Offer Scoring;
- Price Intelligence.

## Validacao final da 8D1

A 8D1 foi validada sobre o baseline `8f0babb`.

Resultados:

- pre-commit aprovado;
- 8 testes isolados da 8D1 aprovados;
- 72 testes acumulados da Etapa 8 aprovados;
- teste explicito de concorrencia aprovado;
- teste explicito de idempotencia aprovado;
- cap de 10 positivas por 24 horas aprovado;
- `rejected` sem autoridade de abuso permaneceu neutro;
- boundaries do contrato aprovadas;
- `git diff --check` aprovado;
- arquivos locais protegidos permaneceram intactos;
- nenhum runtime wiring foi ativado;
- nenhuma reconciliacao historica foi executada;
- nenhuma escrita foi feita no banco live;
- nenhuma escrita em Gamification foi ativada.

A contagem positiva, a decisao da policy, a gravacao no ledger e a atualizacao
do perfil ficam protegidas pela mesma transacao `BEGIN IMMEDIATE`.

## Proximo passo

8D2 - Terminal Community Trust Hook.
