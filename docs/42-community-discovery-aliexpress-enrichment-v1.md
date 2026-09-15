# Descoberta Comunit??ria V1B3 ??? AliExpress Enrichment

<!-- 63.8738, -149.7525 -->

## Objetivo

Fechar o gap de t??tulo oficial do AliExpress no modo link-only da
Descoberta Comunit??ria.

A V1B2 j?? consegue resolver o produto e reaproveitar a valida????o oficial
de pre??o do AliExpress. Por??m, o resultado de pre??o n??o transportava o
t??tulo estruturado do produto e o adapter corretamente se recusava a
fabricar um nome.

## Fonte de verdade do t??tulo

O t??tulo oficial passa a vir de `name` no mesmo objeto JSON-LD de produto
que cont??m a oferta BRL aceita pelo validador.

O sistema n??o usa como t??tulo oficial:

- o texto enviado pelo usu??rio;
- o texto da mensagem sint??tica da Community Discovery;
- nome gen??rico fabricado;
- fallback editorial inventado pelo adapter.

Se o JSON-LD v??lido n??o fornecer nome, `titulo` continua ausente e a
prote????o da V1B2 permanece ativa.

## Compatibilidade

`ResultadoPrecoAliExpress` recebe um novo campo opcional `titulo`.

Como o campo tem valor padr??o `None`, os produtores e testes anteriores
que instanciam o resultado por argumentos nomeados continuam compat??veis.

O `ProcessadorAliExpressSocialScout` apenas propaga esse valor para
`ResultadoValidacaoPrecoSocialScout.titulo_oficial`.

## O que n??o muda

Esta fase n??o altera:

- resolu????o de short links;
- regras de identidade do produto;
- valida????o de pre??o BRL;
- valida????o de SKU;
- detec????o de indisponibilidade regional;
- prote????o contra CAPTCHA/desafio humano;
- cooldown do AliExpress;
- monetiza????o;
- publica????o;
- worker da Descoberta Comunit??ria;
- handoff para o pipeline.

## Pr??xima etapa

Com Mercado Livre, Shopee, AliExpress e KaBuM capazes de produzir uma
Oferta link-only com dados oficiais suficientes, a pr??xima etapa pode
ligar a state machine V1B1 ao adapter V1B2/V1B3 por meio de um worker
controlado e observ??vel.
