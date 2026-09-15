# Descoberta Comunit??ria V1B2 ??? Marketplace Adapter

<!-- 63.8738, -149.7525 -->

## Objetivo

A V1B2 adapta uma `DescobertaComunitaria` j?? reservada em `processing`
para as pe??as de resolu????o e valida????o que j?? existem no Social Scout.

Ela n??o cria um segundo conjunto de scrapers.

## Diferen??a fundamental para o Social Scout

A contribui????o comunit??ria cont??m apenas uma URL.

O Social Scout normalmente recebe tamb??m texto e pre??o observados em uma
mensagem. Por isso os validadores de Shopee, AliExpress e KaBuM possuem
uma trava que rejeita a compara????o quando a mensagem n??o cont??m pre??o.

No fluxo comunit??rio n??o existe um pre??o alegado pelo usu??rio para ser
comparado. O adapter aceita como evid??ncia o pre??o oficial consultado pelo
processador somente quando:

- a identidade do produto foi resolvida;
- o marketplace retornou um pre??o oficial positivo;
- o produto n??o foi marcado como indispon??vel;
- a ??nica raz??o para `nao_verificavel` ?? a aus??ncia do pre??o social.

Outras raz??es de `nao_verificavel` continuam rejeitadas.

## Mercado Livre

O validador atual do Mercado Livre foi desenhado para comparar o snapshot
oficial com um pre??o observado no Social Scout.

A V1B2 reutiliza o mesmo resolvedor, o mesmo snapshot CDP e a mesma
avalia????o do validador, preenchendo a compara????o com o pr??prio pre??o
oficial capturado. Isso evita criar um segundo parser de p??gina.

Este ?? um bridge de compatibilidade expl??cito: o adapter usa os helpers
internos `_capturar_snapshot`, `_numero` e `_avaliar_snapshot` do
validador existente.

## Shopee e KaBuM

Os processadores existentes j?? retornam t??tulo e pre??o oficiais.

Quando o ??nico bloqueio ?? `mensagem_*_sem_preco_base`, a V1B2 promove a
valida????o para o modo link-only e envia o resultado ao
`ConstrutorOfertaSocialScout`.

## AliExpress

O processador atual consegue resolver identidade e validar pre??o, por??m o
`ResultadoValidacaoPrecoSocialScout` produzido por ele ainda n??o exp??e
t??tulo oficial.

Como o construtor exige t??tulo confi??vel, a V1B2 n??o fabrica um nome de
produto. O resultado fica `nao_suportada` com motivo de t??tulo ausente.

Esse gap deve ser resolvido antes de ativar o worker para AliExpress.

## Amazon

A Amazon continua fora do processamento comunit??rio autom??tico nesta
fase. Existe infraestrutura de afiliados/SiteStripe, mas n??o existe ainda
um resolvedor/validador de produto equivalente aos outros marketplaces.

## Sa??da

O adapter retorna um `ResultadoCommunityDiscoveryAdapter` com um dos
estados:

- `oferta_criada`;
- `retry`;
- `rejeitada`;
- `nao_suportada`.

A `Oferta` criada recebe `origem_descoberta = "community_discovery"`.

## Limites

A V1B2 n??o:

- altera o estado da fila;
- marca descoberta como aprovada/rejeitada;
- envia oferta para o `Pipeline`;
- publica conte??do;
- inicia worker autom??tico.

A pr??xima etapa liga o adapter ?? state machine da V1B1 e ao handoff do
pipeline existente.
