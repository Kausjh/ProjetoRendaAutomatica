# Descoberta Comunitária V1B1 — State machine durável

<!-- 63.8738, -149.7525 -->

## Objetivo

Esta fase transforma a fila persistida pela V1A em uma fila de processamento
segura, sem ainda fazer requisições externas aos links enviados.

O banco já possuía os estados `received`, `processing`, `retry`, `approved`
e `rejected`, além de `tentativas`, `disponivel_em` e
`processando_desde`. A V1B1 passa a dar comportamento operacional a esses
campos.

## Reserva atômica

Itens em `received` ou `retry` cujo `disponivel_em` já venceu podem ser
reservados por um processador.

A reserva:

- ocorre sob `BEGIN IMMEDIATE` no SQLite;
- muda o item para `processing`;
- incrementa `tentativas`;
- grava `processando_desde`;
- impede que duas execuções normais assumam o mesmo item ao mesmo tempo.

## Retry

Falhas transitórias devolvem a descoberta para `retry`.

A política padrão usa:

- até 5 tentativas;
- atraso inicial de 60 segundos;
- backoff exponencial;
- teto de 3600 segundos.

Ao atingir o limite de tentativas, a descoberta passa para `rejected`.

## Recuperação de processamento abandonado

Uma descoberta que fique em `processing` além do timeout padrão de
15 minutos volta para `retry`.

Isso protege a fila contra encerramento do processo, reinicialização do
runtime ou falha inesperada depois da reserva.

## Limites desta fase

A V1B1 não:

- acessa a URL enviada pelo usuário;
- resolve redirects;
- consulta marketplace;
- cria `Oferta`;
- envia item para o pipeline;
- publica conteúdo;
- inicia worker automático.

A próxima fase liga esta state machine aos resolvedores e validadores já
existentes, priorizando reutilização do Social Scout em vez de criar uma
arquitetura paralela.
