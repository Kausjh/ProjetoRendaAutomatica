# Offer Comments Core V1

## Status

CONTRATO CONGELADO. IMPLEMENTACAO PENDENTE.

## Contexto

Este e o primeiro contrato executavel do Item 9 - Social / Competitive
Layer V1.

Ele nao cria 9A, 9B ou qualquer outro subnivel de roadmap.

E apenas uma unidade tecnica de implementacao dentro do Item 9.

## Estado atual

Antes deste contrato nao existe backend real de comentarios:

- nenhuma tabela de comentarios;
- nenhuma rota de comentarios;
- nenhuma primitiva de respostas;
- nenhuma primitiva de reactions/helpful.

O hit textual encontrado no preflight nao representa funcionalidade de
comentarios.

## Target V1

O comentario V1 fica vinculado ao produto canonico identificado por:

`canonical_key`

Fonte:

`produtos_canonicos.chave_canonica`

O catalogo canonico e a identidade de usuarios usam bancos SQLite
separados.

Portanto:

- nao existe FK SQLite cruzando os dois bancos;
- o backend deve validar a existencia do produto server-side antes da
  criacao;
- a validacao deve usar o Catalogo Canonico;
- o cliente nao possui autoridade para afirmar que um target existe.

Sinais especificos de uma promocao, como oferta encerrada, cupom
expirado e preco alterado, permanecem em dominio separado.

## Autor

Writes exigem sessao autenticada.

O autor e sempre derivado server-side de:

`contas_usuario.id`

O cliente nao pode selecionar:

- author account;
- impacted account;
- moderator;
- trust recipient.

O account ID interno e o email nunca fazem parte do read model publico.

Enquanto o Perfil Publico opcional ainda nao existir, a superficie pode
usar somente projecoes que nao revelem identidade interna, incluindo
`is_mine`.

## Threads

V1 aceita:

- comentario raiz;
- resposta direta ao comentario raiz.

Profundidade maxima:

`1`

Nao aceita:

- resposta de resposta;
- arvore arbitraria;
- ciclos.

O parent precisa:

- existir;
- pertencer ao mesmo canonical key;
- ser comentario raiz.

## Conteudo

Formato:

`plain_text`

Limite:

`1000` caracteres.

Nao existe:

- HTML;
- Markdown;
- rich text;
- auto-link de URLs.

Isso reduz superficie para XSS, phishing e conteudo ativo.

## Persistencia planejada

Duas estruturas:

1. `offer_comments`
2. `offer_comment_revisions`

`offer_comments` representa identidade e estado atual.

`offer_comment_revisions` e append-only.

Editar um comentario cria uma nova revision.

A revisao anterior nao e sobrescrita.

Delete publico e soft delete.

O corpo de comentario deletado deixa de ser exposto publicamente.

A politica de retencao fisica para auditoria/moderacao sera tratada pela
politica apropriada e nao e decidida pelo cliente.

## Ownership

O autor pode:

- editar o proprio comentario;
- remover o proprio comentario.

Nao pode:

- editar comentario de outra conta;
- remover comentario de outra conta.

Ownership e resolvido exclusivamente server-side.

## Read model

A listagem publica sera paginada.

Defaults:

- root limit: 20;
- root max: 100;
- offset: 0.

Roots:

`created_at DESC, id DESC`

Replies:

`created_at ASC, id ASC`

Campos internos de conta, revision e idempotencia nao sao publicos.

## Idempotencia

Create e edit precisam ser resistentes a retry de rede.

O request identifier:

- e opaco;
- e escopado server-side;
- nao aparece no read model;
- impede que um retry crie comentario duplicado.

## Antiabuso

A API publica de escrita NAO pode ser habilitada apenas com o storage.

Antes de lancar writes publicos precisamos de:

- rate limit por conta;
- rate limit por cliente;
- limite global de buckets;
- Retry-After;
- deteccao de duplicacao de conteudo;
- limites configuraveis;
- fail-closed quando um bucket obrigatorio nao puder ser criado.

O `UserFacingAbuseControls` existente ainda nao cobre comentarios.

## Moderacao

O contrato de Moderation existente ja reserva:

`comment`

como target social futuro.

Porem o ledger live atual suporta somente:

`community_discovery`

Portanto a escrita publica de comentarios nao sera liberada antes de:

- migration/extension explicita de Moderation;
- report de comment;
- decision de moderation;
- regras de takedown/read visibility.

Denuncia continua sendo alegacao.

Quantidade de denuncias nao vira verdade automaticamente.

Somente decisao autoritativa de moderacao pode produzir efeito
autoritativo.

## Trust, Reputation e XP

Criar comentario nao altera diretamente:

- Trust;
- reputation;
- XP.

O cliente nunca escreve esses valores.

Reactions/helpful futuras podem gerar sinais somente por settlement
server-side explicitamente validado.

## Price Intelligence

Comentarios nao possuem autoridade para substituir:

- preco validado;
- disponibilidade validada;
- estado automatico de oferta;
- Price Intelligence.

Sinais comunitarios sao auxiliares.

## AEGIS

Controles congelados:

- Secure by Design;
- Zero Trust;
- Least Privilege;
- Defense in Depth;
- Assume Breach;
- Data Minimization;
- Fail Closed;
- plain text only;
- bounded content;
- bounded pagination;
- shallow threads;
- server-derived author;
- internal account ID privado;
- email privado;
- target validation server-side;
- sem FK cruzando bancos;
- anti-spam antes de writes publicos;
- rate limiting antes de writes publicos;
- moderation antes de writes publicos;
- sem autoridade client-side sobre Trust;
- sem autoridade client-side sobre moderation;
- sem autoridade client-side sobre Price Intelligence.

Nenhuma seguranca existente deve ser silenciosamente enfraquecida.

## Fora de escopo deste contrato

Este freeze nao cria:

- tabela;
- repository;
- service;
- endpoint;
- UI;
- migration;
- rate limiter;
- moderation target live;
- reactions;
- ranking;
- public profile.

## Ordem tecnica planejada

A sequencia de implementacao prevista e:

1. model + repository;
2. service + target validation;
3. abuse controls;
4. moderation target extension;
5. authenticated API;
6. Public App client;
7. Product Comments Surface;
8. helpful reactions.

Essa lista nao cria subniveis no roadmap.

## Proximo passo

Implementar Offer Comments Model + Repository.
