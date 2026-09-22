# Community Moderation Controlled Live Bridge Activation V1 - 8E8B

## Status

8E8B CONCLUIDA E VALIDADA.

## Objetivo

Validar a composition root real de Community Moderation contra o banco live
e provar que a Trust Bridge e efetivamente injetada no Moderation Service.

## Falha inicial de harness

A primeira tentativa parou antes dos imports de Community Moderation porque o
script temporario executado em `%TEMP%` nao possuia a raiz do projeto no
`sys.path`.

Essa tentativa:

- nao importou os componentes;
- nao ativou runtime;
- nao executou reconciliation;
- nao alterou o estado de dominio live;
- nao alterou Git.

O recovery incluiu explicitamente a raiz do projeto no `sys.path`.

## Ativacao controlada

O probe validado usou:

- `database/user_identity.sqlite3`;
- `COMMUNITY_MODERATION_RUNTIME_ATIVO=1` somente no processo filho;
- Authority com token efemero somente em memoria;
- `permitir_schema_activation=True`;
- `executar_reconciliation=False`.

Nenhuma configuracao persistente foi alterada.

## Trust Bridge

A composition root real confirmou:

- Moderation Repository construido;
- Discovery Repository construido;
- Trust Repository construido;
- Authority valida;
- Trust Bridge construida;
- Moderation Service construido;
- Reconciliation Service construido;
- mesma Trust Bridge no Moderation Service;
- mesma Trust Bridge no Reconciliation Service;
- Trust Repository real injetado;
- Discovery Repository real injetado;
- Moderation Repository compartilhado com o Reconciliation Service.

## Reconciliation

Durante o probe a flag ambiental de reconciliation foi colocada em ON apenas
no processo filho.

A chamada usou explicitamente:

`executar_reconciliation=False`

Resultado:

- reconciliation nao executada;
- nenhum resultado de reconciliation;
- nenhuma evidencia Trust criada.

## Estado live

Antes e depois:

- schema inalterado;
- 2 tabelas Moderation;
- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros de foreign key.

## Fronteiras

A 8E8B nao:

- persiste runtime flag;
- reinicia runtime principal;
- cria report;
- cria decision;
- executa confirmed-abuse canary;
- executa reconciliation;
- integra Admin HTTP;
- integra User Reporting API;
- escreve Gamification.

## Validacao final da 8E8B

A 8E8B foi validada sobre o baseline `c61a63f`.

Resultados pre-closure:

- 8 testes isolados aprovados;
- 102 testes acumulados de Moderation aprovados;
- 151 testes Trust + Moderation aprovados;
- pre-commit aprovado.

O probe real confirmou:

- composition root ativa contra o banco live;
- Authority efemera autorizada;
- Moderation Service composto;
- Trust Bridge composta;
- mesma Trust Bridge injetada no Moderation Service;
- mesma Trust Bridge compartilhada com o Reconciliation Service;
- Trust Repository real injetado;
- Discovery Repository real injetado;
- Moderation Repository compartilhado com reconciliation.

A prova de isolamento de reconciliation confirmou que a flag ambiental podia
estar ON no processo do probe enquanto `executar_reconciliation=False`
impedia qualquer reconciliation.

Estado live final:

- schema inalterado;
- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- 0 rows Moderation criadas;
- 0 rows Trust criadas;
- `integrity_check=ok`;
- 0 erros de foreign key.

As flags reais permaneceram OFF depois do probe.

## Proximo passo

8E8C - Controlled Manual Reconciliation.
