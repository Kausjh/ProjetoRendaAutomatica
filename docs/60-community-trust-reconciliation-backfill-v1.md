# Community Trust Reconciliation & Backfill V1 - 8D3

## Status

8D3A CONCLUIDA E VALIDADA.

## Objetivo

Criar a reconciliacao historica e operacional capaz de encontrar uma
Community Discovery terminal que ainda nao possui a evidencia de Community
Trust correspondente.

A 8D3A implementa somente o core e usa bancos temporarios durante os testes.

Nenhum backfill no banco live e executado nesta subetapa.

## Candidato

Um candidato precisa:

- estar `approved` ou `rejected`;
- ainda nao possuir, para a mesma conta, a chave:
  `v1:community-discovery:<discovery_id>`.

Estados `received`, `processing` e `retry` nao entram na reconciliacao.

## Ordem

Os candidatos sao retornados deterministicamente por:

1. `atualizado_em ASC`;
2. `id ASC`.

Isso preserva a ordem historica dos eventos para a janela positiva da policy.

## Processamento

Cada candidato e enviado ao `CommunityTrustTerminalHook` da 8D2.

Esse hook:

- recarrega a discovery autoritativa;
- valida identidade, status e timestamp;
- usa o atomic wiring da 8D1;
- preserva idempotencia.

Uma corrida com o hook live e segura: se a evidencia surgir antes da gravacao
da reconciliacao, a idempotencia do ledger impede duplicacao.

## Falhas

Falha de um candidato nao aborta o restante do lote.

O resultado informa:

- candidatos;
- processados;
- criados;
- idempotentes;
- falhas;
- detalhes das falhas.

O candidato que falhar permanece sem evidencia e pode ser reencontrado numa
execucao posterior.

## Backfill live

A 8D3A NAO executa backfill live.

A 8D3B devera, imediatamente antes da mutacao:

1. verificar `HEAD == origin/main`;
2. verificar integridade SQLite;
3. recontar discoveries terminais;
4. recontar evidencias e perfis;
5. listar apenas candidatos sem evidencia;
6. executar reconciliacao controlada;
7. verificar ledger, profiles, FK e integridade;
8. executar a reconciliacao novamente para provar idempotencia.

## Boundaries

A 8D3A nao ativa:

- runtime composition;
- moderacao;
- Gamification;
- `reputacao_total`;
- API publica;
- app publico.

## Validacao final da 8D3A

A 8D3A foi validada sobre o baseline `33124c9`.

Resultados pre-closure:

- pre-commit aprovado;
- 7 testes isolados da reconciliacao aprovados;
- 95 testes acumulados de Community Discovery + Community Trust aprovados;
- consulta de terminais sem evidencia validada;
- ordenacao deterministica por `atualizado_em ASC, id ASC` validada;
- backfill completo em banco temporario validado;
- segunda execucao sem candidatos validada;
- idempotencia preservada;
- falha individual sem abortar o lote validada;
- boundaries do contrato aprovadas;
- arquivos locais protegidos preservados.

A 8D3A nao realizou leitura ou escrita no banco live.

Nenhum backfill historico real foi executado.

A 8D3B devera auditar o estado real imediatamente antes de qualquer mutacao
e executar o backfill de forma controlada.

## Proximo passo

8D3B - Controlled Live Backfill.
