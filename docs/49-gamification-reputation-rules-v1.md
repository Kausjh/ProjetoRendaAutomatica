# Gamification & Reputation V1 - Regras de Producao

## Etapa 6B

A Etapa 6B fecha a primeira politica real de progressao sobre o
Core Ledger criado na 6A.

Ela define XP, niveis e conquistas. Ainda nao conecta eventos aos
services existentes e ainda nao expoe gamificacao na API ou no app.

## Principio

XP representa progressao de uso.

Reputacao nao e um segundo nome para XP.

Nesta versao, todas as regras de producao possuem
`reputacao_delta = 0`.

Reputacao por contribuicao, qualidade historica e confianca do
contribuidor continuam reservadas para a Etapa 8.

## Eventos de XP

### onboarding_conta_criada

- 40 XP;
- uma vez por conta.

### onboarding_dispositivo_vinculado

- 20 XP;
- apenas o primeiro marco por conta;
- dispositivos adicionais nao geram XP adicional.

### onboarding_preferencias_definidas

- 20 XP;
- apenas o primeiro marco por conta;
- alternar preferencias depois nao gera XP adicional.

### watchlist_produto_adicionado

- 20 XP;
- uma vez por `canonical_key` em cada conta;
- remover e adicionar novamente nao gera XP novamente;
- no maximo 10 novos eventos pontuados por 24 horas.

### watchlist_preco_alvo_definido

- 10 XP;
- uma vez por `canonical_key` em cada conta;
- alterar o preco-alvo depois nao gera XP novamente;
- no maximo 10 novos eventos pontuados por 24 horas.

## Acoes sem XP

Login, logout, remocao de item da Lista, revogacao de dispositivo e
acoes repetidas de configuracao nao concedem XP.

Community Discovery tambem nao entra nesta etapa. Missoes e
recompensas comunitarias pertencem a Etapa 7; reputacao e confianca
do contribuidor pertencem a Etapa 8.

## Niveis

Os thresholds cumulativos da V1 sao:

1. 0 XP
2. 100 XP
3. 250 XP
4. 450 XP
5. 700 XP
6. 1000 XP
7. 1400 XP
8. 1900 XP
9. 2500 XP
10. 3200 XP

Os thresholds fazem parte do ruleset versionado. O nivel continua
derivado do XP e nao ganha uma segunda fonte de verdade.

## Conquistas e badges

As conquistas V1 sao derivadas deterministicamente do ledger e do
nivel. Elas nao possuem tabela propria nesta etapa.

- `radar_ligado`: primeiro item na Lista;
- `lista_5`: cinco produtos distintos na Lista;
- `lista_10`: dez produtos distintos na Lista;
- `primeiro_alvo`: primeiro preco-alvo;
- `setup_completo`: conta, dispositivo, preferencias e primeiro item;
- `nivel_5`: nivel 5 de progressao.

## Anti-farming

A 6B reutiliza integralmente as garantias da 6A:

- idempotencia fail-closed;
- janela atomica;
- relogio de persistencia controlado pelo servidor.

A estrategia de chave definida nesta politica sera aplicada pela 6C.

## Fronteiras

A 6B nao altera runtime, API, app, Community Discovery, curadoria,
Price Intelligence ou scoring de ofertas.

## Proximo passo

A 6C fara o wiring server-side dos eventos reais para o ruleset V1,
incluindo reconciliacao idempotente de marcos ja existentes.
