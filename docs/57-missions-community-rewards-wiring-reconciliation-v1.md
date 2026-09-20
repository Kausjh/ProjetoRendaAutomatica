# Missions & Community Rewards V1 - Wiring 7C1

## Objetivo

A 7C1 implementa a ponte entre uma descoberta comunitaria `approved` e o
Mission Engine.

Ela tambem implementa a reconciliacao historica de descobertas que ja estejam
aprovadas.

Nenhum componente e ativado no banco real ou no runtime nesta etapa.

## Fonte do evento

O evento aceito e exclusivamente:

`community_discovery_approved`

A origem e:

`community_discovery_v1`

Estados `received`, `processing`, `retry` e `rejected` nao geram progresso.

## Wiring

Cada descoberta aprovada e aplicada as tres missoes do catalogo V1.

Todas usam a instancia:

`lifetime`

A chave de idempotencia e:

`v1:community-approved:{discovery_id}`

Como o escopo do ledger inclui a missao, a mesma chave pode alimentar as tres
missoes sem colisao entre elas.

O metadata persistido e deliberadamente minimo e estavel:

`{"status": "approved"}`

Isso evita que mudancas futuras em canonical key ou outros campos auxiliares
transformem um replay legitimo em colisao semantica.

## Resultado esperado com uma descoberta

No primeiro processamento de uma unica descoberta aprovada:

- tres eventos de progresso sao criados;
- a missao de primeira aprovada atinge 1/1;
- uma recompensa `pending` de 20 XP e criada;
- a missao de cinco fica em 1/5;
- a missao de dez fica em 1/10.

No segundo processamento da mesma descoberta:

- nenhum novo evento e criado;
- tres eventos sao reconhecidos como idempotentes;
- nenhuma nova recompensa e criada.

## Reconciliacao

A reconciliacao le todas as linhas `approved` de `community_discoveries`,
ordenadas por `criado_em` e `id`.

O processo e paginado e idempotente.

Qualquer falha fica registrada no resultado.

Na futura ativacao, live wiring so podera ser habilitado quando a reconciliacao
terminar sem falhas.

## Ponto futuro de live wiring

O preflight confirmou que a transicao real para `approved` acontece em:

`CommunityDiscoveryQueueService.aprovar`

A 7C1 nao modifica esse servico.

A injecao sera feita apenas na 7C2, depois que as tabelas reais forem criadas e a
reconciliacao historica tiver sido concluida com sucesso.

A aprovacao da descoberta continuara sendo o fluxo principal. Uma eventual
falha de Mission Engine nao deve desfazer a aprovacao ja persistida.

## Fronteiras

A 7C1 nao:

- cria tabelas de missao no banco real;
- altera `CommunityDiscoveryQueueService`;
- ativa live wiring;
- altera o runtime;
- liquida rewards no ledger de gamificacao;
- altera o ruleset de gamificacao;
- cria API;
- altera Public App;
- concede reputacao comunitaria;
- calcula contributor trust;
- cria ranking;
- altera scoring;
- altera Price Intelligence.

## Proximo passo

7C2 - Controlled Runtime Activation.
