# Community Trust Public Read Model V1 - 8F1

## Status

8F1 CONCLUIDA E VALIDADA.

## Objetivo

A 8F1 cria a fundacao read-only para apresentar ao proprio usuario
o estado de Community Trust.

Esta etapa nao adiciona rota HTTP e nao altera o Public App.

## Autoridade

A autoridade continua sendo:

`community_trust_evidence_ledger`

A tabela materializada:

`community_trust_profiles`

continua sendo somente uma projecao do ledger.

O cliente nunca escreve Trust.

## Public projection

A projecao publica do perfil contem apenas:

- `evidencias_total`;
- `positivas_total`;
- `negativas_total`;
- `neutras_total`;
- `atualizado_em`.

Nao sao expostos:

- `conta_id`;
- `chave_idempotencia`;
- `origem`;
- `origem_id`;
- `metadados`;
- identificadores de moderador;
- justificativas internas;
- familias internas de abuso;
- policy internals.

## Score

A 8F1 nao inventa score numerico.

O projeto continua sem formula publica de score de Trust.

As contagens do ledger permanecem fatos separados.

## Zero state

Usuario sem evidencia possui:

- total = 0;
- positivas = 0;
- negativas = 0;
- neutras = 0;
- `atualizado_em = null`.

## Fail closed

O controller User-Facing falha com HTTP 503 quando o read service
nao estiver disponivel.

Conta inativa e rejeitada como sessao invalida.

## AEGIS Security Impact Review

A 8F1 segue:

- Secure by Design;
- Least Privilege;
- Data Minimization;
- Fail Closed;
- Defense in Depth;
- nao regressao das protecoes existentes.

A etapa nao introduz:

- endpoint publico novo;
- porta nova;
- secret novo;
- dependencia nova;
- banco novo;
- schema novo;
- caminho novo de escrita;
- escrita em Trust;
- escrita em Moderation;
- escrita em Gamification.

Portanto nao existe aumento persistente de superficie de ataque
nesta etapa.

## Arvore 8F

A arvore da 8F e exatamente:

- 8F1 - Trust Public Read Model;
- 8F2 - Authenticated Trust Profile API;
- 8F3 - Trust Evidence History API;
- 8F4 - Public App Trust Client;
- 8F5 - Public App Trust Surface;
- 8F6 - Final Closure.

Nao existem subniveis escondidos.

## Validacao final

A 8F1 foi validada sobre o baseline `94fecd2`.

Read model:

- Community Trust continua read-only;
- source of truth permanece o evidence ledger;
- projection materializada continua sendo `community_trust_profiles`;
- zero state validado;
- perfil publico limitado a contagens e `atualizado_em`;
- `conta_id` nao e exposto;
- evidence history nao e exposto nesta etapa;
- metadata interna nao e exposta;
- idempotency keys nao sao expostas;
- moderator actor nao e exposto;
- score numerico de Trust nao foi definido nem inventado.

Boundaries:

- nenhuma rota HTTP adicionada;
- nenhum server wiring alterado;
- nenhum schema alterado;
- nenhuma escrita no banco live;
- nenhuma escrita em Trust;
- nenhuma escrita em Moderation;
- nenhuma escrita em Gamification;
- Public App nao alterado.

Resultados pre-closure:

- 12 testes isolados 8F1 aprovados;
- 111 testes Community Trust aprovados;
- 194 testes Community Moderation aprovados;
- 61 testes Public Mobile aprovados;
- 70 testes backend Reporting aprovados.

Live:

- integrity check `ok`;
- zero foreign key errors;
- 0 moderation reports;
- 0 moderation decisions;
- 2 Trust evidence;
- 1 Trust profile.

## Security Impact Review - Protocolo AEGIS

A 8F1 preserva:

- Secure by Design;
- Least Privilege;
- Defense in Depth;
- Data Minimization;
- Fail Closed;
- nao regressao das protecoes existentes.

Nao houve:

- endpoint publico novo;
- porta persistente nova;
- secret novo;
- dependencia nova;
- database novo;
- write path novo;
- ampliacao persistente da superficie de ataque;
- exposicao de campos internos;
- enfraquecimento silencioso de seguranca.

A fronteira HTTP autenticada permanece deliberadamente adiada
para a 8F2.

## Proximo passo

8F2 - Authenticated Trust Profile API.
