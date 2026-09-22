# Community Moderation Public App Report Submission V1 - 8E11B

## Status

8E11B CONCLUIDA E VALIDADA.

## Objetivo

Entregar a primeira superficie visual de denuncia no Public App.

A 8E11B usa exclusivamente o client e o read model concluidos na
8E11A.

## Entrada

A tela `/discover` continua sendo a superficie comunitaria existente.

Cada `DiscoveryCard` recebe a acao:

`Denunciar problema`

O `CommunityDiscoveryItem.id` e enviado como `targetId` para a tela
`/report`.

Nenhum novo community feed e criado nesta etapa.

## Tela de denuncia

Nova rota:

`/report`

Parametros:

- `targetId` obrigatorio;
- `targetLabel` apenas para contexto visual.

A tela exige sessao autenticada.

## Motivos

As sete categorias publicas sao:

- spam;
- fraud;
- malicious_link;
- abuse;
- off_topic;
- duplicate;
- other.

Nenhum motivo novo e inventado no aplicativo.

## Detalhes

O campo de detalhes e opcional.

A UI limita o texto a 1000 caracteres como protecao de experiencia,
sem alterar o contrato do backend.

A interface tambem orienta o usuario a nao enviar senhas, documentos
ou outros dados pessoais.

## Envio

A tela usa:

`useCreateCommunityReport`

A camada criada na 8E11A continua responsavel por gerar e enviar
`Idempotency-Key`.

A chave tecnica nao aparece na UI.

Durante o envio o botao fica desabilitado.

Depois de sucesso a tela tambem bloqueia um novo envio acidental.

## Semantica

A interface informa explicitamente que:

- a denuncia e uma alegacao para revisao;
- denunciar nao confirma abuso ou fraude;
- denunciar nao remove automaticamente a contribuicao;
- o envio nao grava Trust diretamente;
- o envio nao cria decisao administrativa.

## Fronteira

A 8E11B nao adiciona:

- historico de denuncias;
- status de denuncias;
- detalhe de denuncia;
- community feed;
- alteracao de backend;
- alteracao de banco;
- migration;
- nova feature flag;
- restart;
- canario live.

Historico e status permanecem reservados para a 8E11C.

## Validacao final

A 8E11B foi validada sobre o baseline `e63344d`.

Resultados pre-closure:

- estado materializado recuperado sem reaplicar implementacao;
- auditoria estrutural aprovada;
- auditoria pos-format aprovada;
- pre-commit aprovado;
- typecheck do Public App aprovado;
- 10 testes isolados da 8E11B aprovados;
- 47 testes da regressao Public Mobile aprovados;
- 70 testes do backend Reporting aprovados.

A superficie concluida possui:

- acao `Denunciar problema` em `DiscoveryCard`;
- rota `/report`;
- sete motivos publicos;
- detalhes opcionais;
- uso de `useCreateCommunityReport`;
- idempotencia mantida na camada de client;
- bloqueio de envio duplicado enquanto pending;
- bloqueio de reenvio acidental apos sucesso.

A interface preserva a semantica de moderacao:

- report e alegacao para revisao;
- report nao confirma abuso;
- report nao remove o target;
- report nao grava Trust diretamente;
- report nao cria decisao administrativa.

Estado live:

- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros de foreign key;
- nenhuma escrita live;
- nenhuma alteracao de schema live.

Historico, status e detalhe de reports permanecem reservados
para a 8E11C.

## Proximo passo

8E11C - Report Status / History Surface.
