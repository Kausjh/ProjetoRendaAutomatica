# App Público V3

<!-- 63.8738, -149.7525 -->

Este documento mantém o escopo do produto público do Radar de Ofertas enquanto o desenvolvimento passa a priorizar o aplicativo.

## Princípio

O aplicativo não deve ser apenas uma vitrine da API. Ele precisa transformar a inteligência já existente no Radar em uma experiência útil para quem compra: descobrir, entender, acompanhar e receber a oferta certa no momento certo.

## Base já existente

- autenticação e sessão;
- catálogo e listagem de produtos;
- detalhe de produto e histórico de preço;
- watchlist;
- alertas;
- preferências de conta;
- registro do aparelho e push;
- integração com a Application API;
- identidade visual do Radar.

## Frentes do App V3

### Feed e descoberta

A Home deve evoluir de uma listagem simples para uma superfície de descoberta. O feed deverá destacar oportunidades reais, quedas relevantes e, quando o backend estiver pronto para isso, conteúdo personalizado por watchlist, interesses e comportamento.

A busca deverá evoluir para pesquisa de catálogo em escala, sem depender permanentemente de filtrar apenas a página já carregada no aparelho.

### Produto e inteligência de preço

A tela de produto deve expor o que diferencia o Radar:

- preço atual;
- melhor oferta disponível;
- histórico visual;
- contexto do preço;
- queda real;
- anomalias e sinais relevantes quando disponíveis;
- marketplace;
- ação clara para abrir a oferta;
- ação de adicionar ou remover da Lista.

### Lista e alertas

Salvar um produto precisa ser rápido. A watchlist deve permitir acompanhamento, preço-alvo e preferência por queda de preço. Os alertas devem levar diretamente ao produto que disparou o evento.

### Feed personalizado

O feed personalizado deverá aproveitar watchlist, preferências e sinais de interesse. Ele só deve ser chamado de personalizado quando os dados realmente forem usados pelo backend; não haverá personalização simulada na interface.

### Descoberta comunitária

Usuários também serão uma fonte de descoberta do Radar.

Fluxo pretendido:

1. o usuário encontra uma promoção e envia o link pelo app;
2. o Radar registra a contribuição com a conta de origem;
3. o link passa por identificação de fonte e produto;
4. o produto passa pela identidade canônica e deduplicação;
5. preço e contexto passam pelo Price Intelligence;
6. regras de qualidade e segurança decidem se a descoberta é aproveitável;
7. uma oferta aprovada pode alimentar catálogo, feed, alertas, push e outros canais.

Uma descoberta enviada por usuário **não deve ser publicada diretamente**. A comunidade fornece candidatos; o Radar continua responsável por validar a informação.

Reputação, ranking, gamificação e eventuais recompensas de contribuidores fazem parte da evolução dessa frente, mas as regras exatas devem ser definidas antes de serem apresentadas no produto.

### Crescimento

Depois do núcleo de produto:

- compartilhamento;
- indicação;
- campanhas;
- aquisição;
- conteúdo orientado pelos próprios dados do Radar;
- integração com novas superfícies públicas.

## Bloco atual

O primeiro incremento do App V3 adiciona ação rápida de salvar/remover produtos da Lista diretamente na Home, usando a watchlist real da API. Nenhum mock é criado e nenhuma nova dependência externa é necessária.

A descoberta comunitária será construída de ponta a ponta; a interface não deve fingir que envia contribuições enquanto o endpoint correspondente ainda não existir.
