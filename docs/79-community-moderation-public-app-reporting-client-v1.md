# Community Moderation Public App Reporting Client V1 - 8E11A

## Status

8E11A CONCLUIDA E VALIDADA.

## Objetivo

Preparar a camada de cliente e read model do Public App para a
superficie de denuncias comunitarias entregue pela 8E10.

A 8E11A nao adiciona interface visual.

## Recovery

A primeira tentativa da 8E11A aplicou somente
`ApiRequestOptions.idempotencyKey` e parou em um anchor textual do
`http-transport.ts`.

A recovery preservou essa alteracao ja materializada e continuou a
implementacao sem restore, reset ou reaplicacao do arquivo parcial.

## PublicApiClient

Operacoes autenticadas adicionadas:

- `listCommunityReports`;
- `getCommunityReport`;
- `createCommunityReport`.

Rotas:

- `GET /me/reports`;
- `GET /me/reports/{report_id}`;
- `POST /me/reports`.

## Idempotencia

`ApiRequestOptions` possui a opcao estreita `idempotencyKey`.

Quando preenchida, `HttpApiTransport` envia:

`Idempotency-Key`

Nao foi criado suporte generico para headers arbitrarios.

O Public App gera:

`mobile-${Crypto.randomUUID()}`

## Read model

Motivos:

- spam;
- fraud;
- malicious_link;
- abuse;
- off_topic;
- duplicate;
- other.

Estados:

- received;
- under_review;
- resolved.

Resumo:

- id;
- targetType;
- targetId;
- reason;
- status;
- createdAt;
- updatedAt.

Detalhe adiciona:

- details.

## React Query

Hooks:

- `useCommunityReports`;
- `useCommunityReport`;
- `useCreateCommunityReport`.

A criacao preenche o cache do detalhe e invalida a familia
`community-reports`.

## Privacidade

Nao sao modelados no Public App:

- reporter_conta_id;
- chave de idempotencia persistida;
- moderator actor;
- resultado administrativo;
- justificativa do moderador;
- authority origin;
- dados internos de Trust.

## Fronteiras

A 8E11A nao:

- altera tela;
- adiciona rota Expo;
- adiciona botao;
- altera backend;
- altera banco;
- altera schema;
- ativa runtime;
- reinicia servidor;
- executa canario live.

## Arvore 8E11

- 8E11A - Public App Reporting Client / Read Model;
- 8E11B - Report Submission Surface;
- 8E11C - Report Status / History Surface.

## Validacao final

A 8E11A foi validada sobre o baseline `520034c`.

Resultados pre-closure:

- auditoria estrutural aprovada;
- pre-commit aprovado;
- typecheck do Public App aprovado;
- 13 testes isolados da 8E11A aprovados;
- 36 testes da regressao Public Mobile aprovados;
- 70 testes do backend Reporting 8E10 aprovados.

A recovery preservou a alteracao parcial em `api-types.ts` e nao
reaplicou esse patch.

A camada concluida possui:

- suporte estreito a `Idempotency-Key`;
- `listCommunityReports`;
- `getCommunityReport`;
- `createCommunityReport`;
- reporting types;
- reporting presenter;
- React Query hooks para lista, detalhe e criacao.

A etapa nao adiciona UI.

Nao sao modelados dados internos de moderacao ou Trust.

Estado live:

- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros de foreign key;
- nenhuma escrita live;
- nenhuma alteracao de schema live.

## Proximo passo

8E11B - Report Submission Surface.
