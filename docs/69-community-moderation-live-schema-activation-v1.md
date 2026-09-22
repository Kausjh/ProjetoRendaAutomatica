# Community Moderation Live Schema Activation V1 - 8E7

## Status

8E7 CONCLUIDA E VALIDADA.

## Escopo

A 8E7 ativou exclusivamente o schema live de Community Moderation.

### 8E7A

Foi criado e validado um recovery point SQLite anterior a qualquer schema
de Moderation.

Backup:

`logs/reports/backups/user_identity_pre_8e7b_20260922_155416148.sqlite3`

SHA-256:

`74f8bb85b28738d535ad73622f394143dd3c671703469472beb18cc852ad1526`

Schema pre-ativacao:

`ef8c9baec8e50420626a724069ddcebcca284fecc95103a82dcfb557a231b93b`

### 8E7B

A ativacao foi ensaiada em copia do recovery point antes do write live.

O live recebeu exclusivamente:

- `community_moderation_reports`;
- `community_moderation_decisions`;
- indices pertencentes a essas tabelas.

Estado final:

- 0 reports;
- 0 decisions;
- 2 evidencias Trust;
- 1 profile Trust;
- `integrity_check=ok`;
- 0 erros FK.

Schema pos-ativacao:

`710c43d5e42c78647c2476de7e55b87b3c27e9acdcac67e66d9f61e53788ec2b`

### 8E7C

O live foi auditado somente em modo read-only.

A prova de rollback ocorreu em copia temporaria:

1. restauracao do backup pre-8E7B;
2. confirmacao do schema anterior;
3. confirmacao de 0 tabelas Moderation;
4. reaplicacao do `CommunityModerationRepository`;
5. retorno exato ao schema pos-8E7B.

Nenhum restore foi executado no banco live.

Um lock temporario do Windows durante limpeza de arquivo SQLite temporario
na primeira tentativa nao invalidou a prova funcional. O recovery repetiu
a prova usando cleanup best-effort, retirando a limpeza temporaria da
fronteira de corretude.

## Fronteiras

A 8E7 nao ativou:

- runtime principal;
- Moderation Service live;
- Trust Bridge live;
- reconciliation live;
- Admin HTTP;
- User Reporting API.

## Proximo passo

8E8 - Controlled Runtime Wiring.
