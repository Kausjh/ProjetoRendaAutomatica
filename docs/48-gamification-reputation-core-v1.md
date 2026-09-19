# Gamification & Reputation V1 - Core Ledger

## Etapa 6A

A Etapa 6A cria a fundacao persistente de progressao e reputacao.
Ela nao define ainda os valores de XP/reputacao usados em producao e
nao expoe gamificacao no aplicativo.

## Fonte de verdade

`gamification_events` e o ledger auditavel.

Cada evento registra:

- conta;
- chave de idempotencia;
- tipo;
- origem e origem_id;
- delta de XP;
- delta de reputacao;
- versao da regra;
- metadados;
- instante do evento;
- instante de persistencia.

`gamification_profiles` e um snapshot materializado para leitura rapida.
O snapshot e atualizado na mesma transacao que grava o evento.

## Regras

`ConjuntoRegrasGamificacao` e versionado e injetado no service.

A 6A nao possui regras de producao. Isso e deliberado: o backend nao
deve inventar pontos antes de a politica de progressao ser fechada.

O nivel e derivado dos thresholds do ruleset e nao ganha uma fonte de
verdade paralela no banco.

## Anti-farming

Duas protecoes entram na fundacao:

1. chave de idempotencia unica por conta;
2. limite temporal opcional por regra, verificado dentro de uma
   transacao `BEGIN IMMEDIATE`.

Retries idempotentes sao resolvidos antes da verificacao do limite.

Uma mesma chave de idempotencia reutilizada com tipo, origem, deltas, versao de regra ou metadados diferentes falha de forma fechada, em vez de mascarar uma colisao.

A janela anti-farming usa o instante de persistencia controlado pelo servidor. `ocorrido_em` permanece no ledger como dado auditavel, mas nao pode deslocar artificialmente a janela de limite.

## Fronteiras

A Etapa 6A:

- nao cria rota publica;
- nao altera o Public App;
- nao concede XP nem reputacao automaticamente por Community Discovery;
- nao implementa missoes da Etapa 7;
- nao implementa confianca de contribuidor da Etapa 8;
- nao altera preco, curadoria ou qualidade objetiva de ofertas;
- nao influencia Price Intelligence;
- nao cria ranking publico.

A Community Discovery e uma futura fonte natural de eventos porque ja
possui autoria e estado persistente, mas sua semantica de reputacao deve
respeitar a fronteira da Etapa 8.

## Proximo passo

A Etapa 6B definira as regras reais de progressao, thresholds de nivel
e a camada de conquistas/badges sobre este ledger.
