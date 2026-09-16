# Descoberta Comunit??ria V1B4 ??? Worker controlado

<!-- 63.8738, -149.7525 -->

## Decis??o arquitetural

A Descoberta Comunit??ria entra no runtime como uma **fonte do pipeline
existente**, implementando o mesmo contrato `BaseScraper.buscar_ofertas`
que as demais fontes.

N??o foi criado um segundo `ExecutorPipeline`, nem um caminho paralelo
direto para Cat??logo Can??nico, Price Intelligence ou Alert Engine.

Fluxo:

```text
community_discoveries
    -> CommunityDiscoveryQueueService
    -> CommunityDiscoveryMarketplaceAdapter
    -> CommunityDiscoveryScraper
    -> Hunter V2 / ColetorOfertas
    -> valida????o / classifica????o / Pipeline
    -> ExecutorPipeline
    -> Cat??logo Can??nico
    -> Price Intelligence
    -> Alert Engine
```

## Durabilidade e ACK

Ao reservar uma descoberta, a state machine V1B1 move o item para
`processing` e incrementa `tentativas`.

Se o adapter produzir uma Oferta, o scraper n??o aprova a descoberta
imediatamente. Ele mant??m apenas uma associa????o em mem??ria entre a
Oferta e o id da descoberta.

A fonte de verdade continua sendo o SQLite. Se o processo morrer antes
do ACK, o item permanece em `processing` e a recupera????o de
processamento expirado da V1B1 o devolve para `retry`.

O ACK acontece por `confirmar_handoff`, reaproveitando o mecanismo j??
consumido pelo `ColetorOfertas` e pelo `ExecutorPipeline`.

- `pipeline_processada` -> `approved`;
- `coletor_duplicada` -> `approved`;
- rejei????o terminal do coletor -> `rejected`;
- aus??ncia de ACK -> nenhuma transi????o terminal.

Quando dispon??vel ap??s o processamento, `chave_produto_canonica` ??
persistida como `canonical_key` na aprova????o.

## Controle de ativa????o

O wiring existe, mas permanece desligado por padr??o.

```text
COMMUNITY_DISCOVERY_PIPELINE_ATIVO=0
COMMUNITY_DISCOVERY_MAX_POR_EXECUCAO=3
```

Somente quando `COMMUNITY_DISCOVERY_PIPELINE_ATIVO` estiver explicitamente
ativo o `CommunityDiscoveryScraper` ser?? registrado junto ??s fontes do
pipeline.

Esta fase n??o altera o ambiente, n??o reinicia o supervisor e n??o consome
as contribui????es reais atualmente em `received`.

## Pr??xima etapa

A V1B5 dever?? fazer uma ativa????o can??rio controlada, observar o
processamento real de poucas contribui????es e validar estado da fila,
Cat??logo Can??nico, Price Intelligence, Alert Engine e sa??de do runtime
antes de ampliar o volume.
