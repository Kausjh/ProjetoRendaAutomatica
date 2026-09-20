# Missions & Community Rewards V1 - Catalog 7B

## Objetivo

A 7B define o catalogo de missoes de producao e a politica de recompensa XP.

Nenhuma missao e ativada no runtime nesta etapa.

## Evento confiavel

A V1 usa apenas:

`community_discovery_approved`

Uma simples submissao em `received` nao gera progresso.

Tambem nao geram progresso:

- `processing`;
- `retry`;
- `rejected`.

A razao e impedir que volume bruto de links seja convertido em XP antes da
validacao server-side da contribuicao.

## Catalogo V1

O catalogo possui tres missoes lifetime:

| Missao | Alvo | XP |
| --- | ---: | ---: |
| Primeira descoberta aprovada | 1 | 20 |
| Cinco descobertas aprovadas | 5 | 50 |
| Dez descobertas aprovadas | 10 | 100 |

O teto total de recompensa lifetime desta V1 e 170 XP.

## Recorrencia

A V1 nao possui missao diaria, semanal ou mensal.

Todas as missoes usam:

`instancia_chave = lifetime`

Isso reduz risco de:

- duplicacao por timezone;
- virada de janela;
- replay temporal;
- farming recorrente;
- bugs de reconciliacao.

Recorrencia podera ser adicionada posteriormente com uma politica de instancia
explicitamente versionada.

## Economia

Os thresholds atuais de Gamification & Reputation sao:

`0, 100, 250, 450, 700, 1000, 1400, 1900, 2500, 3200`

O catalogo V1 distribui no maximo 170 XP lifetime.

Com o estado real observado no preflight de 140 XP, completar todas as tres
missoes levaria o perfil a 310 XP.

Isso representa progressao relevante sem transformar Community Discovery em uma
fonte ilimitada de XP.

## Settlement futuro

Cada missao possui um event type de gamificacao proprio:

- `mission_reward_community_primeira_aprovada`;
- `mission_reward_community_cinco_aprovadas`;
- `mission_reward_community_dez_aprovadas`.

Os event types sao fixos porque cada recompensa possui XP fixo.

A 7B ainda nao adiciona esses eventos ao ruleset de gamificacao e nao liquida
nenhuma concessao `pending`.

## Idempotencia de Community Discovery

O futuro wiring deve usar:

`v1:community-approved:{discovery_id}`

Assim, uma mesma descoberta aprovada pode ser reprocessada ou reconciliada sem
incrementar uma missao duas vezes.

## Reconciliacao

Antes de ativar live wiring, a etapa seguinte devera reproduzir de forma
idempotente todas as descobertas historicas que ja estejam em `approved`.

Somente depois de reconciliacao completa o wiring ao vivo podera ser ativado.

## Fronteiras

A 7B nao implementa:

- runtime;
- wiring de Community Discovery;
- execucao da reconciliacao;
- settlement de XP;
- API;
- Public App;
- reputacao comunitaria;
- contributor trust;
- ranking social;
- alteracao de scoring;
- alteracao de Price Intelligence.

## Proximo passo

7C - Community Approved Wiring & Reconciliation.
