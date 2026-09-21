# Community Trust Model V1 - 8A

## Status

CONCLUIDA.

## Objetivo

Definir a autoridade, semantica e fronteiras de Community Trust antes de
persistencia, scoring, wiring ou exposicao publica.

## Separacao de dominios

- XP, nivel, conquistas e badges continuam pertencendo a Gamification.
- Community Trust mede confianca verificavel no historico de contribuicoes.
- `gamification_profiles.reputacao_total` nao e a fonte de verdade de Trust.
- `reputacao_total` fica reservado como projecao server-side futura.
- opiniao social e evidencia objetiva permanecem semanticamente separadas.

## Fonte de verdade

A fonte autoritativa planejada e um Community Trust Evidence Ledger proprio.

A Etapa 8A nao cria o ledger. Isso pertence a 8B.

## Evidencia de Community Discovery

Estados terminais elegiveis como fonte de evidencia:

- `approved`;
- `rejected`.

Estados nao terminais nao geram evidencia de Trust:

- `received`;
- `processing`;
- `retry`.

Uma descoberta `approved` pode se tornar evidencia positiva.

Uma descoberta `rejected` nao e automaticamente evidencia negativa.

O campo `motivo_status` precisa ser classificado antes de qualquer impacto
negativo. Rejeicoes tecnicas, sistemicas ou fora do controle do contribuidor
sao neutras por padrao.

## Scoring

A 8A nao define pontos, pesos, thresholds ou formula de score.

A politica numerica e antiabuso pertence a 8C.

## Gamification

O core existente consegue representar `reputacao_delta`, mas as regras de
producao atuais mantem reputacao comunitaria em zero.

A 8A preserva essa regra.

Qualquer projecao futura de Community Trust para `reputacao_total` precisa:

- ser server-side;
- ser idempotente;
- derivar do dominio autoritativo de Trust;
- nao criar uma segunda fonte de verdade;
- nao alterar XP ou nivel por efeito colateral.

## Fronteiras preservadas

A 8A nao implementa:

- tabelas novas;
- runtime wiring;
- escrita em Gamification;
- escrita em Community Discovery;
- API publica;
- superficie no Public App;
- moderacao;
- denuncias;
- comentarios, votos ou reacoes;
- influencia em Offer Scoring;
- influencia em Price Intelligence.

## Proxima subetapa

8B - Community Trust Core Ledger.
