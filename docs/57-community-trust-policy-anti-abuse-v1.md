# Community Trust Production Policy & Anti-Abuse V1 - 8C

## Status

IMPLEMENTACAO CONCLUIDA; VALIDACAO E REVIEW PENDENTES.

## Objetivo

Definir como eventos terminais de Community Discovery podem se transformar em
classificacao de Trust sem ligar o runtime de producao.

## Principio

Status terminal sozinho nao define confianca.

`approved` nao significa automaticamente evidencia positiva.

`rejected` nao significa automaticamente evidencia negativa.

A politica considera status, motivo, idempotencia, janela antiabuso e versao
da regra.

## Impacto numerico

A V1 define impacto por evidencia:

- `positive`: +1;
- `neutral`: 0;
- `negative`: -1.

Isso nao cria um score agregado.

Isso nao cria campo de score no perfil.

Isso nao escreve em `gamification_profiles.reputacao_total`.

## Evidencia positiva

Somente aprovacao da familia `pipeline_processada` e candidata positiva na V1.

A familia `coletor_duplicada` permanece `neutral`.

O objetivo e impedir farming de Trust atraves de URLs diferentes que terminem
em uma duplicata ja conhecida pelo coletor.

## Janela antiabuso positiva

A V1 permite no maximo 10 evidencias positivas contadas por conta em uma
janela movel de 86400 segundos.

Apos o limite, a evidencia terminal continua auditavel, mas sua classificacao
fica `neutral`.

O padrao 10/86400 reaproveita um mecanismo ja utilizado pelas regras de
Gamification.

O limite de 30 submissions por hora de Community Discovery continua sendo
controle upstream independente e nao substitui o teto de Trust.

`positivas_na_janela` e apenas contexto para a funcao pura de politica.

No runtime da 8D, essa contagem nao pode vir do cliente nem de estado local
nao autoritativo.

A contagem deve vir do ledger server-side e a verificacao da janela precisa
ser protegida atomicamente junto da escrita da evidencia. Isso impede duas
execucoes concorrentes de observarem o mesmo contador e ultrapassarem o teto.

A implementacao desse enforcement atomico pertence a 8D.

## Evidencia negativa

Uma rejeicao comum nunca e negativa automaticamente.

Negative exige um motivo explicito de abuso confirmado:

- `abuso_confirmado`;
- `spam_confirmado`;
- `fraude_confirmada`;
- `link_malicioso_confirmado`.

O texto do motivo sozinho nao constitui autoridade para penalizacao.

Mesmo que `motivo_status` pertenca a uma familia de abuso confirmado, a V1
exige tambem contexto server-side explicito de confirmacao autoritativa.

Sem essa confirmacao adicional, a classificacao permanece `neutral`.

O pipeline atual de Community Discovery nao emite esses motivos nem fornece
essa confirmacao autoritativa.

Portanto, rejeicoes atualmente produzidas pelo pipeline permanecem neutras.

## Rejeicoes neutras

Permanecem neutras por padrao:

- falhas tecnicas;
- erros de API;
- retries esgotados;
- timeout;
- marketplace ou capacidade ainda nao suportada;
- produto nao resolvido;
- produto indisponivel;
- validacao nao aprovada;
- preco oficial invalido;
- falha de construcao;
- item fora de nicho;
- qualquer motivo terminal ainda nao classificado.

Motivo desconhecido falha fechado para `neutral`, nunca para `negative`.

## Idempotencia

A chave prevista e:

`v1:community-discovery:{discovery_id}`

Uma descoberta terminal gera no maximo uma evidencia de Trust por conta.

A mesma URL normalizada da mesma conta ja e idempotente no dominio upstream.

## Auditoria

A decisao preserva contexto suficiente para futura persistencia:

- status da descoberta;
- motivo terminal;
- canonical key quando existir;
- numero de tentativas;
- contagem positiva anterior na janela;
- confirmacao autoritativa de abuso quando aplicavel;
- versao da politica.

## Fronteiras da 8C

A 8C nao faz:

- wiring com Community Discovery;
- escrita no ledger live;
- alteracao de schema;
- escrita em Gamification;
- projecao em `reputacao_total`;
- API publica;
- Public App;
- moderacao;
- influencia em Offer Scoring;
- influencia em Price Intelligence.

O wiring server-side pertence a 8D.

## Proximo passo

Validar e revisar a Production Trust Policy V1.
