# Community Trust Public App Client V1 - 8F4

## Status

8F4 CONCLUIDA E VALIDADA.

## Objetivo

A 8F4 adiciona ao Public App somente a camada de cliente/read-model
necessaria para consumir Community Trust.

Nao existe UI nova nesta etapa.

## Backend consumido

Perfil:

`GET /api/v1/me/trust`

Historico:

`GET /api/v1/me/trust/evidence`

O `PublicApiClient` usa os paths relativos:

- `/me/trust`;
- `/me/trust/evidence`.

Isso preserva a infraestrutura HTTP ja existente do app.

## Autenticacao

Os dois requests usam:

`requiresUserSession: true`

E continuam utilizando:

- `HttpApiTransport`;
- sessao existente em secure runtime storage;
- configuracao de infraestrutura existente;
- envelope User-Facing existente.

Nenhum novo mecanismo de auth foi criado.

## Read model do perfil

O app modela somente:

- `evidenceTotal`;
- `positiveTotal`;
- `negativeTotal`;
- `neutralTotal`;
- `updatedAt`;
- `modelVersion`;
- `numericScoreDefined`.

`numericScoreDefined` deve permanecer `false`.

O app nao inventa score numerico.

## Read model do historico

Cada item modela somente:

- `type`;
- `classification`;
- `occurredAt`.

Classificacoes aceitas:

- `positive`;
- `negative`;
- `neutral`.

Nao sao modelados:

- account ID interno;
- evidence ID interno;
- idempotency key;
- origem;
- origem_id;
- motivo;
- policy version;
- metadata bruta;
- moderator actor.

## Presenter

Os presenters sao fail-closed.

Payloads inesperados geram:

`CommunityTrustPayloadError`

Sao validados:

- inteiros nao negativos;
- model version positiva;
- score numerico obrigatoriamente falso;
- classification allowlist;
- limit;
- offset;
- quantidade igual ao tamanho da pagina.

## React Query

Hooks:

- `useCommunityTrustProfile`;
- `useCommunityTrustEvidenceHistory`.

Paginacao:

- default limit 20;
- minimo 1;
- maximo 100;
- default offset 0;
- offset minimo 0.

A conta nao aparece na query key porque o backend continua self-only
e a identidade vem exclusivamente da sessao autenticada.

## AEGIS Security Impact Review

A 8F4 nao adiciona endpoint de rede.

Ela apenas passa a consumir os endpoints autenticados existentes.

Controles preservados:

- Zero Trust;
- Least Privilege;
- Defense in Depth;
- Data Minimization;
- Fail Closed;
- sessao existente;
- auth de infraestrutura existente;
- self-only backend contract;
- ausencia de account selector;
- bounded pagination;
- strict payload validation.

Nao ha:

- secret novo;
- storage novo;
- dependencia nova;
- endpoint servidor novo;
- write path novo;
- database change;
- UI nova;
- navigation change.

## Fora de escopo

A superficie visual de Community Trust pertence exclusivamente a 8F5.

## Arvore 8F

- 8F1 - completed;
- 8F2 - completed;
- 8F3 - completed;
- 8F4 - Public App Trust Client;
- 8F5 - Public App Trust Surface;
- 8F6 - Final Closure.

Nao existem subniveis escondidos.

## Validacao final

A 8F4 foi validada sobre o baseline `7583dae`.

Resultados pre-closure:

- pre-commit aprovado;
- TypeScript typecheck aprovado;
- 13 testes isolados 8F4 aprovados;
- 6 arquivos historicos Public Mobile;
- 61 testes historicos Public Mobile aprovados;
- 7 arquivos Public Mobile na suite combinada;
- 74 testes Public Mobile combinados aprovados;
- 11 arquivos Community Trust backend;
- 149 testes Community Trust backend aprovados.

Duas falhas anteriores foram exclusivamente do harness:

1. `ast` nao havia sido importado no script temporario de
   implementacao;
2. a descoberta automatica de testes Public Mobile procurava o texto
   literal `apps/public-mobile`, enquanto o teste Trust monta o path
   com `pathlib`.

Nenhuma das duas falhas era funcional.

A implementacao nao foi reaplicada para mascarar esses erros.

Garantias do client:

- `HttpApiTransport` existente reutilizado;
- sessao segura existente reutilizada;
- infraestrutura auth existente reutilizada;
- `getCommunityTrustProfile`;
- `listCommunityTrustEvidence`;
- envelope User-Facing existente;
- strict payload validation;
- paginacao limitada;
- ausencia de account selector;
- ausencia de numeric score inventado;
- ausencia de identificadores internos de evidence;
- ausencia de contexto interno sensivel no read model.

Escopo preservado:

- nenhuma UI Trust nesta etapa;
- nenhuma alteracao de navegacao;
- nenhum endpoint servidor novo;
- nenhum write path novo;
- nenhuma escrita em banco;
- nenhuma escrita de Trust;
- runtime principal permaneceu Running;
- Health Monitor permaneceu habilitado;
- nenhum restart do runtime;
- SHA-256 do banco live permaneceu inalterado.

## Security Impact Review - Protocolo AEGIS

Foram validados:

- Secure by Design;
- Zero Trust;
- Least Privilege;
- Defense in Depth;
- Data Minimization;
- Fail Closed;
- reuse do transporte existente;
- reuse da sessao existente;
- reuse da auth de infraestrutura;
- self-only backend contract;
- ausencia de account selector;
- bounded pagination;
- strict presenter validation;
- ausencia de numeric score inventado;
- ausencia de internal evidence context no modelo publico;
- ausencia de write path novo;
- ausencia de nova superficie persistente de servidor.

Nenhuma protecao existente foi silenciosamente enfraquecida.

## Proximo passo

8F5 - Public App Trust Surface.
