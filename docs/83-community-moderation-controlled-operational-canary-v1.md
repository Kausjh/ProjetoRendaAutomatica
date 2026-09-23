# Community Moderation Controlled Operational Canary V1 - 8E12B

## Status

8E12B CONCLUIDA E VALIDADA.

## Objetivo

A 8E12B exercita o caminho operacional real da Community Moderation
sem alterar o banco live e sem iniciar o runtime persistente do
Projeto Renda Automatica.

## Estrategia

O canario executa:

1. preflight real de standby no banco live;
2. snapshot read-only do banco live;
3. clone SQLite temporario via backup;
4. ativacao real de Community Moderation contra o clone;
5. `COMMUNITY_MODERATION_RUNTIME_ATIVO=1` somente no processo;
6. reconciliation explicitamente desabilitada;
7. Admin HTTP real em `127.0.0.1` e porta efemera;
8. leitura autenticada da fila;
9. rejeicao de token administrativo incorreto;
10. probe de decisao contra report inexistente;
11. snapshot final do clone;
12. encerramento do servidor;
13. restauracao das variaveis de ambiente;
14. remocao do clone;
15. novo snapshot read-only do banco live.

## Runtime

O canario chama diretamente:

`ativar_community_moderation_runtime`

com:

- `permitir_schema_activation=True`;
- `executar_reconciliation=False`.

A ativacao ocorre somente contra o clone temporario.

O `runtime.py` persistente nao e iniciado.

## Admin HTTP

O canario sobe `ServidorStatusAdministrativo` em loopback e porta
efemera.

Probes:

- GET autorizado em `/moderation/reports?limite=1&offset=0` -> 200;
- GET com token errado -> 401;
- POST de decision contra report inexistente -> 404.

O ultimo probe atravessa o endpoint autoritativo sem criar decision.

## Segredo

O token real pode ser carregado do process environment ou `.env`.

O valor nunca aparece no JSON do canario, logs estruturados,
contract ou documentacao.

## Banco live

O banco live e fonte somente de leitura.

Antes e depois do canario sao comparados:

- SHA-256 do arquivo principal;
- contagens operacionais;
- `schema_version`;
- `integrity_check`;
- foreign keys.

Qualquer alteracao falha o canario.

## Clone

No clone temporario sao comparados:

- contagens antes/depois;
- schema version antes/depois;
- integridade;
- foreign keys.

O clone deve ser removido ao final.

## Reconciliation

A reconciliation permanece explicitamente OFF.

A 8E12B nao valida reconciliacao por escrita.

## Teardown no Windows

O servidor administrativo usa HTTP com threads.

No Windows pode existir uma pequena janela entre o encerramento do
servidor e a liberacao final dos handles associados ao clone SQLite.

Por isso o canario:

- encerra o servidor;
- remove referencias aos services usados pelo servidor;
- libera referencias ao runtime temporario;
- executa garbage collection;
- tenta remover o diretorio temporario ate 20 vezes;
- aguarda 100 ms entre tentativas quando necessario;
- falha fechado se o clone continuar presente.

Esse retry existe somente no teardown do clone temporario.

Ele nao mascara alteracoes no banco live nem altera os demais gates
do canario.

## Limites

A 8E12B nao:

- inicia o runtime persistente;
- altera feature flag persistente;
- grava no banco live;
- altera schema live;
- cria report live;
- cria decision live;
- confirma abuso live;
- escreve Trust live.

## Arvore

A arvore continua exatamente:

- 8E12A - concluida;
- 8E12B - Controlled Operational Canary;
- 8E12C - Final Operational Closure.

Nao existem subniveis escondidos.

## Validacao final

A 8E12B foi validada sobre o baseline `016ee2c`.

O canario operacional real retornou `ready=true` e zero blockers.

Ativacao controlada validada:

- runtime real ativado somente contra clone temporario;
- `schema_activation_authorized=true`;
- componentes do runtime presentes;
- reconciliation permaneceu desabilitada;
- runtime persistente nao foi iniciado.

Admin HTTP real em loopback:

- leitura autorizada -> HTTP 200;
- quantidade de reports lida -> 0;
- token incorreto -> HTTP 401;
- decision contra report inexistente -> HTTP 404;
- nenhuma decision foi criada.

Teardown Windows-safe:

- servidor administrativo encerrado;
- referencias dos services liberadas;
- referencias do runtime temporario liberadas;
- garbage collection executado;
- cleanup com ate 20 tentativas;
- delay de 100 ms entre retries;
- clone temporario removido;
- variaveis de ambiente restauradas.

Banco live:

- SHA-256 inalterado;
- contagens inalteradas;
- schema version inalterada;
- integrity check `ok`;
- 0 foreign key errors;
- 0 moderation reports;
- 0 moderation decisions;
- 2 Trust evidence;
- 1 Trust profile.

Resultados pre-closure:

- 11 testes isolados da 8E12B aprovados;
- 183 testes Community Moderation aprovados;
- 61 testes Public Mobile aprovados;
- 70 testes backend Reporting aprovados.

A 8E12B nao:

- iniciou runtime persistente;
- executou reconciliation;
- gravou no banco live;
- alterou schema live;
- criou report live;
- criou decision live;
- expos o token administrativo.

A arvore operacional passa a ser:

- 8E12A - concluida;
- 8E12B - concluida;
- 8E12C - Final Operational Closure.

## Proximo passo

8E12C - Final Operational Closure.
