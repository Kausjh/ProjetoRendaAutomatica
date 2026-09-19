# Gamification & Reputation V1 - Domain Event Wiring

## Etapa 6C1

A 6C1 conecta os eventos de progressao aos services que ja
representam as acoes reais do usuario.

O runtime ainda nao instancia a gamificacao nesta subetapa.
Sem configuracao explicita, os services continuam com o mesmo
comportamento anterior.

## Eventos

### Conta criada

Uma conta persistida com sucesso tenta registrar
`onboarding_conta_criada`.

### Primeiro dispositivo

Somente o primeiro dispositivo historico da conta tenta registrar
`onboarding_dispositivo_vinculado`.

Rotacao de token, reativacao ou dispositivos posteriores nao geram
novo XP.

### Preferencias

A primeira persistencia de preferencias tenta registrar
`onboarding_preferencias_definidas`.

Atualizacoes posteriores nao geram novo XP.

### Watchlist

A criacao de uma nova `canonical_key` tenta registrar
`watchlist_produto_adicionado`.

Atualizar o item nao gera XP novamente. Remover e adicionar a mesma
canonical key tambem nao gera novamente porque a chave de
idempotencia pertence ao ledger.

### Preco-alvo

A primeira transicao de ausencia de preco-alvo para um valor
nao nulo tenta registrar `watchlist_preco_alvo_definido`.

Alterar o valor depois nao gera XP novamente.

## Falhas

Gamificacao e efeito secundario.

Uma falha, conflito ou limite da camada de gamificacao nao desfaz
nem bloqueia uma operacao de conta, dispositivo, preferencias ou
watchlist que ja foi persistida com sucesso.

A reconciliacao da 6C2 podera reparar eventos ausentes.

## Fronteiras

A 6C1 nao altera:

- runtime;
- API publica;
- Public App;
- Community Discovery;
- reputacao comunitaria;
- missoes;
- Price Intelligence;
- scoring de ofertas.

## Proximo passo

A 6C2 fara a composicao no runtime e uma reconciliacao idempotente
do estado historico ja existente antes da ativacao operacional.
