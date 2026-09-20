# Missions & Community Rewards V1 - Core 7A

## Objetivo

A 7A cria o nucleo persistente do Mission Engine.

O progresso, a conclusao e a elegibilidade de recompensa sao sempre
determinados pelo servidor.

## Persistencia

O core possui tres estruturas:

- `mission_progress_events`: ledger auditavel de eventos de progresso;
- `mission_progress`: snapshot agregado por conta, missao, ruleset e instancia;
- `mission_reward_grants`: concessoes de recompensa criadas na conclusao.

A criacao da concessao de recompensa ocorre na mesma transacao que conclui a
missao.

## Idempotencia

A chave efetiva considera:

`conta + missao + ruleset + instancia + chave_idempotencia`

Repetir o mesmo evento e seguro.

Reutilizar a mesma chave com semantica diferente falha fechado.

Depois que uma missao esta concluida, novos eventos para a mesma instancia nao
criam progresso nem recompensas adicionais.

## Recompensas

O core 7A representa recompensa de XP.

Ao concluir uma missao, ele cria uma concessao com status `pending`.

A 7A ainda nao envia esse XP para o ledger de Gamification & Reputation.

Essa liquidacao sera feita em etapa posterior com uma chave idempotente baseada
na propria concessao, permitindo recuperar com seguranca de falhas entre os dois
passos.

Reputacao nao e recompensa da Etapa 7.

## Community Discovery

A 7A ainda nao faz wiring com Community Discovery.

A regra arquitetural para a etapa seguinte e que uma simples submissao nao deve
contar como contribuicao util.

Missoes comunitarias deverao consumir eventos server-side confiaveis, como a
transicao de uma descoberta para `approved`.

Isso evita premiar spam em `received`, itens rejeitados ou retries.

## Fronteiras

A 7A nao implementa:

- catalogo de missoes de producao;
- reconciliacao de descobertas existentes;
- runtime;
- API publica;
- tela no Public App;
- reputacao comunitaria;
- contributor trust;
- ranking;
- alteracao do scoring de ofertas;
- alteracao de Price Intelligence.

## Proximo passo

7B - Production Mission Catalog & Reward Policy.
