# Community Trust Public App Surface V1 - 8F5

## Status

8F5 CONCLUIDA E VALIDADA.

## Objetivo

A 8F5 materializa Community Trust na interface publica.

A superficie escolhida e a tela de Perfil (`account`), no mesmo
modelo arquitetural ja utilizado por Gamification e Missions.

Nao existe nova rota.

Nao existe novo item na bottom navigation.

## Componente

Componente:

`TrustPanel`

Integracao:

`apps/public-mobile/app/account.tsx`

O painel e montado apenas quando existe sessao autenticada.

## Dados exibidos

Resumo:

- total de evidencias;
- positivas;
- neutras;
- negativas;
- versao do modelo publico.

Historico:

- tipo da evidencia;
- classificacao;
- timestamp.

## Score numerico

A UI nao inventa score numerico.

O produto apresenta explicitamente que Community Trust nao possui
nota numerica publica nesta versao.

## Estados de UX

O painel possui:

- loading;
- erro;
- retry;
- refresh manual;
- empty state;
- estado com dados.

## Fonte de verdade

A UI utiliza exclusivamente:

- `useCommunityTrustProfile`;
- `useCommunityTrustEvidenceHistory`.

O cliente nao:

- recalcula perfil;
- cria evidencia;
- altera classificacao;
- calcula score.

## Privacidade

Nao sao renderizados:

- account ID;
- evidence ID;
- idempotency key;
- origem;
- origem_id;
- motivo interno;
- policy version;
- raw metadata;
- moderator actor.

## AEGIS Security Impact Review

A 8F5 adiciona apenas superficie visual.

Ela nao adiciona nova superficie persistente de servidor.

Controles:

- Secure by Design;
- Zero Trust;
- Least Privilege;
- Defense in Depth;
- Data Minimization;
- Fail Closed.

A UI nao manipula diretamente:

- `Authorization`;
- Bearer token;
- `X-User-Session`;
- segredo de infraestrutura;
- account selector.

Todo transporte e identidade continuam encapsulados nas camadas
existentes da 8F4.

## Fora de escopo

A 8F5 nao altera:

- backend;
- banco;
- Trust ledger;
- moderacao;
- gamificacao;
- rotas;
- bottom navigation.

## Arvore 8F

- 8F1 - completed;
- 8F2 - completed;
- 8F3 - completed;
- 8F4 - completed;
- 8F5 - Public App Trust Surface;
- 8F6 - Final Closure.

Nao existem subniveis escondidos.

## Validacao final

A 8F5 foi validada sobre o baseline `73569b5`.

Resultados pre-closure:

- pre-commit aprovado;
- TypeScript typecheck aprovado;
- 13 testes isolados 8F5 aprovados;
- 61 testes historicos Public Mobile aprovados;
- 88 testes Public Mobile combinados aprovados;
- 75 testes da Account Surface Regression aprovados;
- 149 testes Community Trust backend aprovados.

A falha inicial da 8F5 foi exclusivamente um falso positivo do
harness de seguranca.

A regra original procurava a substring `fetch(` e, por isso,
interpretava chamadas legitimas de React Query como `refetch()` como
se fossem chamadas diretas a `fetch()`.

A correcao tornou a verificacao precisa:

- chamada direta standalone a `fetch()` continua proibida;
- `refetch()` do React Query continua permitido;
- nenhum arquivo de produto foi alterado pela recovery;
- nenhum teste funcional foi removido ou relaxado.

Garantias da superficie:

- integrada ao Perfil;
- nenhuma rota dedicada nova;
- nenhum item novo na bottom navigation;
- resumo publico de Community Trust;
- historico publico de evidencias;
- loading state;
- error/retry state;
- empty state;
- refresh manual;
- nenhum score numerico inventado;
- nenhum account selector;
- nenhum identificador interno renderizado;
- nenhum contexto interno de evidence renderizado.

Escopo preservado:

- nenhum endpoint backend novo;
- nenhuma alteracao de banco;
- nenhuma escrita de Trust;
- nenhum controle de escrita;
- runtime principal permaneceu Running;
- Health Monitor permaneceu habilitado;
- nenhum restart de runtime;
- SHA-256 do banco live permaneceu inalterado.

## Security Impact Review - Protocolo AEGIS

Foram validados:

- Secure by Design;
- Zero Trust;
- Least Privilege;
- Defense in Depth;
- Data Minimization;
- Fail Closed;
- reuse do Trust Client existente;
- UI sem transporte HTTP direto;
- UI sem manipulacao direta de auth headers;
- UI sem manipulacao direta de User Session;
- ausencia de account selector;
- ausencia de internal identifiers;
- ausencia de internal evidence context;
- ausencia de numeric score inventado;
- ausencia de standalone `fetch()`;
- ausencia de write controls;
- ausencia de nova superficie persistente de servidor;
- preservacao do runtime;
- preservacao do estado live.

Nenhuma protecao existente foi silenciosamente enfraquecida.

## Proximo passo

8F6 - Final Closure.
