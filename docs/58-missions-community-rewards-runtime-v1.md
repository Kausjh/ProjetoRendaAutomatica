# Missions & Community Rewards V1 - Runtime 7C2

## Objetivo

A 7C2 prepara a ativacao controlada do Mission Engine no runtime real.

A implementacao separa duas fases:

1. composicao e testes sem tocar o banco de producao;
2. commit seguido de restart controlado para ativacao real.

## Ordem de ativacao

O runtime principal:

1. compoe identidade e personalizacao;
2. ativa e reconcilia gamification;
3. ativa o Mission Engine;
4. inicializa as tabelas mission_*;
5. reconcilia todas as community discoveries approved;
6. somente se a reconciliacao terminar sem falhas habilita a flag
   `MISSIONS_COMMUNITY_RUNTIME_ATIVO=1`;
7. inicia os demais componentes e o orquestrador.

O processo de pipeline herda o ambiente do runtime pai.

## Live wiring

O `CommunityDiscoveryQueueService` recebe um hook generico de pos-aprovacao.

A ordem e obrigatoria:

1. persistir `approved`;
2. reler a descoberta persistida;
3. executar o hook;
4. retornar a descoberta aprovada.

Se o hook falhar, a aprovacao ja persistida nao e revertida.

Isso preserva Community Discovery como fluxo principal e permite que a proxima
reconciliacao recupere qualquer evento de missao perdido.

## Worker

`CommunityDiscoveryScraper` cria o Mission live wiring somente quando a flag
`MISSIONS_COMMUNITY_RUNTIME_ATIVO` vale `1`.

Se a composicao do hook falhar, o worker registra erro e continua sem bloquear
Community Discovery.

## Recompensa

A 7C2 pode criar `mission_reward_grants` com status `pending`.

Ela nao liquida XP no ledger de gamification.

O perfil real deve continuar com:

- 140 XP;
- 7 eventos;
- reputacao 0.

A liquidacao pertence a 7D.

## Roadmap de produto

A mesma mudanca formaliza:

- Etapa 7 em execucao;
- comentarios, respostas, reacoes, perfis publicos opcionais e rankings na
  Etapa 9;
- Community Reputation & Trust mantida na Etapa 8;
- Public App Experience / Visual Polish como frente transversal;
- imagens de produtos e cards ricos sem esperar pela Etapa 9.

## Fronteiras

A 7C2 nao implementa:

- settlement de rewards;
- reputacao comunitaria;
- contributor trust;
- comments backend;
- ranking backend;
- perfil social backend;
- Missions Read API;
- tela de missoes;
- mudanca de offer scoring;
- mudanca de Price Intelligence.

## Proximo passo

Review e commit da implementacao 7C2, seguidos de restart controlado de
producao e auditoria do SQLite real.
