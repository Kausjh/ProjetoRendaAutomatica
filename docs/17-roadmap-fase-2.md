# Roadmap — Fase 2

## Objetivo

A Fase 1 foi concluída com o roadmap 30/30.

O backend já possui coleta, catálogo canônico, inteligência de preços,
Promotion/Opportunity Intelligence, Alert Engine, Application API, identidade
de usuários, preferências, watchlists, matching personalizado e outbox
persistente de notificações.

A Fase 2 transforma essa infraestrutura em produto público utilizável e evolui
o sistema em direção a personalização, comunidade, reputação, gamificação e
novas superfícies.

---

## Princípios

A evolução da Fase 2 segue estes princípios:

1. contratos públicos antes da interface;
2. identidade e autorização sempre derivadas server-side;
3. clientes não recebem segredos de infraestrutura;
4. push permanece fail-closed enquanto não estiver operacionalmente validado;
5. nenhuma personalização é simulada;
6. reputação, XP, missões, ranking ou recompensas só existem no produto quando
   houver regras explícitas, persistência e proteção contra abuso;
7. regras de negócio permanecem no backend;
8. novas superfícies reutilizam contratos existentes.

---

# Ordem oficial

## Etapa 1 — User-Facing API V1

**Status: CONCLUÍDA**

### Objetivo

Expor de forma segura as capacidades de usuário existentes internamente.

### Entregas

- contrato público de autenticação;
- separação entre credencial de infraestrutura e sessão de usuário;
- cadastro;
- login;
- logout;
- `/me`;
- preferências;
- watchlist;
- rate limiting;
- controles contra abuso;
- isolamento entre contas.

### Gate

Um usuário deve conseguir administrar somente os próprios dados usando
contratos públicos.

Esse gate foi atingido.

---

## Etapa 2 — Public App MVP

**Status: CONCLUÍDA COMO MVP**

### Objetivo

Criar o primeiro cliente público utilizável.

### Entregas

- React Native + Expo + TypeScript;
- sessão persistente;
- login e cadastro;
- catálogo de ofertas;
- detalhe do produto;
- histórico de preço;
- watchlist;
- preço-alvo;
- conta e preferências;
- alertas;
- integração somente com contratos públicos.

O MVP continua evoluindo através da frente App Público V3.

### Gate

O aplicativo deve conseguir autenticar um usuário e utilizar as capacidades
públicas sem depender do control plane administrativo.

Esse gate foi atingido para o escopo MVP.

---

## Etapa 3 — Device Registration V1

**Status: CONCLUÍDA — VALIDADA EM ANDROID REAL**
### Objetivo

Associar instalações do aplicativo público a contas para permitir push.

### Implementado

- persistência de dispositivos;
- múltiplos dispositivos por conta;
- ativação e revogação;
- rotação de token;
- isolamento entre contas;
- `GET /api/v1/me/devices`;
- `PUT /api/v1/me/devices/{instalacao_id}`;
- `DELETE /api/v1/me/devices/{instalacao_id}`;
- aquisição via `expo-notifications`;
- bootstrap autenticado no app;
- binding do dispositivo com o backend;
- proteção para ambientes onde push remoto não está disponível.

### Validação operacional

Gate concluído em 19/09/2026.

Um development build Android real:

- obteve um Expo Push Token válido;
- vinculou a instalação autenticada;
- persistiu um dispositivo Android ativo no backend;
- manteve o token fora dos logs.

A validação foi realizada em dispositivo físico.

---

## Etapa 4 — Push Dispatcher V1

**Status: CONCLUÍDA — SMOKE REAL VALIDADO**
### Objetivo

Conectar a Notification Outbox aos dispositivos reais por um provedor de push.

### Implementado

- Expo Push Gateway;
- envio em batch;
- tickets;
- receipts;
- persistência das tentativas;
- payload personalizado;
- associação com dispositivos ativos;
- retry;
- tratamento de `DeviceNotRegistered`;
- idempotência;
- worker contínuo;
- integração ao Runtime Unificado;
- supervisão e restart do processo;
- proteção contra processamento stale;
- redaction de push tokens em logs.

### Segurança operacional

O dispatcher permanece desativado por padrão por meio de
`RUNTIME_PUSH_DISPATCHER_ATIVO=false`.

Isso é deliberado: implementação disponível não equivale a entrega real
validada.

### Validação operacional

Gate concluído em 19/09/2026 pela combinação de validação real e cobertura
persistente da orquestração.

O smoke controlado em Android físico comprovou:

- um único push real;
- ticket Expo com `status=ok`;
- receipt Expo com `status=ok`;
- entrega visual da notificação no aparelho;
- nenhum push token exposto;
- runtime automático permaneceu desligado.

A suíte da orquestração cobre adicionalmente:

- reserva da outbox em `processing`;
- permanência em `processing` até receipt;
- transição para `delivered` após receipt `ok`;
- retry em falhas recuperáveis;
- falha terminal quando aplicável;
- tratamento de `DeviceNotRegistered`.

O smoke físico não consumiu a outbox de produção. As transições persistentes
foram validadas em SQLite isolado com os mesmos repositories e services usados
pela orquestração real.

---

## Etapa 5 — Personalized Feed V1

**Status: CONCLUÍDA**

### Objetivo

Transformar sinais reais de usuário em uma superfície personalizada.

### Sinais consolidados na V1

- watchlist;
- preço-alvo;
- marketplaces preferidos;
- catálogo canônico e Price Intelligence;
- score de relevância calculado no backend;
- motivos de personalização devolvidos ao cliente.

Histórico comportamental de interação não faz parte do contrato fechado da
V1 e permanece como possibilidade de evolução futura.

### Escopo entregue

- motor `PersonalizedFeedService`;
- endpoint autenticado `GET /api/v1/me/feed`;
- identidade derivada exclusivamente da sessão do usuário;
- paginação versionada;
- integração ao Public App;
- Home usando o feed personalizado como fonte principal;
- motivos visíveis para watchlist, preço-alvo atingido e marketplace preferido;
- ações rápidas de Lista preservadas;
- pull-to-refresh preservado;
- estado vazio sem fallback genérico disfarçado;
- pontuação numérica interna de relevância não exposta visualmente.

### Evidências de conclusão

- `df4d25a` — core do Personalized Feed;
- `e2284ff` — exposição pela User-Facing API;
- `bfc5707` — data layer do Public App;
- `f61a044` — Home personalizada;
- typecheck do Public App aprovado;
- 43 testes direcionados aprovados antes e depois dos hooks;
- pre-commit aprovado;
- Application API atualizada e `GET /api/v1/me/feed` comprovado localmente;
- mesma rota comprovada pelo transporte Tailscale usado pelo app;
- smoke real aprovado no Samsung M52 com duas oportunidades da Lista
  aparecendo em `Seu radar personalizado` com o motivo `Na sua watchlist`.

### Gate

**CUMPRIDO em 19/09/2026.**

A Home autenticada passou a refletir sinais reais da conta sem recorrer ao
catálogo genérico como falsa personalização. O smoke no Android físico
confirmou que itens adicionados à Lista alimentam o feed personalizado real.

---

## Etapa 6 — Gamification & Reputation V1

**Status: CONCLUÍDA — VALIDADA DE PONTA A PONTA**
### Objetivo

Criar uma fundação persistente de progressão e reputação.

### Implementado

- eventos de progresso;
- XP;
- níveis;
- conquistas;
- badges;
- reputação;
- histórico auditável;
- regras versionadas;
- limites contra farming e abuso.

Gamificação não deve alterar a avaliação objetiva de preço ou qualidade de uma
oferta.

### Validacao operacional

Concluida em 20/09/2026.

A Etapa 6 foi validada de ponta a ponta com estado real:

- ledger persistente;
- reconciliacao de usuarios existentes;
- regras versionadas;
- idempotencia e limites anti-farming;
- runtime ativo e fail-safe;
- API autenticada `GET /api/v1/me/gamification`;
- 140 XP reais;
- nivel 2 derivado do ruleset;
- reputacao 0;
- 7 eventos no ledger;
- progresso de 40/150 XP;
- 110 XP restantes;
- conquistas e badges derivados server-side;
- superficie real no Public App;
- smoke visual aprovado em Samsung SM-M526B.

O nivel continua derivado dos thresholds do ruleset e nao e persistido como
fonte paralela em `gamification_profiles`.

O cliente nao pode escrever XP, reputacao ou eventos.

Missoes e recompensas comunitarias permanecem reservadas para a Etapa 7.
Community Reputation & Trust permanece reservada para a Etapa 8.

---

## Etapa 7 — Missions & Community Rewards V1

**Status: CONCLUÍDA — 7A, 7B, 7C1, 7C2, 7D, 7E, 7F E 7G CONCLUÍDAS**

### Objetivo

Transformar contribuições úteis em missões e recompensas verificáveis.

### Regras fechadas

- progresso server-side;
- conclusão server-side;
- reward grant auditável;
- idempotência por conta, missão, ruleset, instância e chave;
- apenas `community_discovery_approved` gera progresso na V1;
- missões V1 `lifetime`;
- teto inicial de recompensas: 170 XP;
- reputação comunitária permanece fora da Etapa 7.

### Catálogo V1

| Missão | Alvo | Recompensa |
| --- | ---: | ---: |
| Primeira descoberta aprovada | 1 | 20 XP |
| Cinco descobertas aprovadas | 5 | 50 XP |
| Dez descobertas aprovadas | 10 | 100 XP |

### Subetapas

- **7A — Mission Engine Core:** concluída.
- **7B — Production Mission Catalog & Reward Policy:** concluída.
- **7C1 — Approved Wiring + Reconciliation Service:** concluída.
- **7C2 — Controlled Runtime Activation:** concluída e validada em produção.
- **7D — Reward Settlement to Gamification:** concluída e validada em produção.
  - **7D1 — Core Settlement:** concluída.
  - **7D2 — Runtime Reconciliation:** concluída.
  - **7D3 — Guarded Runtime Wiring:** concluída.
  - **7D4 — Controlled Production Activation:** concluída.
  - **7D5 — Live Reward Settlement:** concluída, ativa e validada em produção.
- **7E — Missions Read API:** concluída e validada em produção.
  - **7E1 — Mission Read Core:** concluída.
  - **7E2 — HTTP Wiring:** concluída.
- **7F — Public App Missions Surface:** concluída e validada no Android real.
  - **7F1 — Client / Read Model:** concluída no commit `3a3c65c`.
  - **7F2 — Public App Missions Panel:** concluída no commit `b3393c8`.
  - **7F3 — Real Android Validation:** concluída no Samsung SM-M526B / Android 13.
- **7G — Fechamento operacional:** concluída.

### Validação operacional da 7C2

Concluída em 20/09/2026 sobre o commit `c2e05f6`.

O ambiente real confirmou:

- três tabelas `mission_*`;
- três eventos de missão;
- três snapshots de progresso;
- um reward `pending` de 20 XP;
- segunda reconciliação com 0 eventos novos e 3 idempotentes;
- runtime final `HEALTHY`;
- supervisor preservado;
- Chrome/CDP preservado;
- SQLite íntegro;
- zero erros de foreign key;
- gamification preservada em 140 XP, 7 eventos e reputação 0.

### Validação operacional da 7D

Concluída em 20/09/2026.

A 7D implementa settlement de rewards de missão para Gamification de forma idempotente e auditável.

A implementação foi dividida em cinco passos:

- **7D1 — Core Settlement:** settlement recoverable e idempotente por reward grant;
- **7D2 — Runtime Reconciliation:** reconciliação de rewards pendentes;
- **7D3 — Guarded Runtime Wiring:** integração ao runtime atrás de feature flag;
- **7D4 — Controlled Production Activation:** primeira liquidação real validada;
- **7D5 — Live Reward Settlement:** settlement executado durante o fluxo live de aprovação.

A implementação live da 7D5 foi commitada em `93533dc` (`feat: add live mission reward settlement`).

A produção confirmou:

- `MISSIONS_COMMUNITY_LIVE_REWARD_SETTLEMENT_ATIVO=true`;
- wiring real `MissionCommunityLiveSettlementWiring`;
- um reward de `community_primeira_aprovada` concedido com 20 XP;
- zero rewards `pending` ao final;
- um reward `granted`;
- um evento `mission_reward_*`;
- canário idempotente com 0 eventos novos e 3 eventos de missão idempotentes;
- 0 novos rewards no canário;
- 0 novos eventos de Gamification no canário;
- 0 XP duplicado;
- reputação comunitária preservada em 0;
- SQLite `integrity_check=ok`;
- zero erros de foreign key;
- runtime e Chrome/CDP `HEALTHY`.

Durante o canário final, o estado de Gamification permaneceu em 190 XP, 10 eventos e reputação 0 antes e depois da execução.

### Validação operacional da 7E

Concluída em 20/09/2026 sobre o commit `cba7423`.

O ambiente real confirmou:

- runtime reciclado cirurgicamente para o PID `16144`, com supervisor preservado;
- Application API `HEALTHY` em produção;
- `GET /api/v1/me/missions` ativo e protegido por `X-User-Session`;
- smoke autenticado real com HTTP 200;
- 3 missões retornadas pelo ruleset `missions-community-rewards-production-v1`;
- 1 missão concluída, 2 em andamento, 0 não iniciadas;
- 1 reward `granted`, 0 `pending`;
- `community_primeira_aprovada` em 1/1 com 20 XP concedidos;
- `community_cinco_aprovadas` em 1/5 com reward de 50 XP ainda `locked`;
- `community_dez_aprovadas` em 1/10 com reward de 100 XP ainda `locked`;
- leitura comprovadamente read-only, sem alteração de missions ou Gamification;
- sessão temporária do canário revogada ao final;
- SQLite íntegro e 0 erros de foreign key.

### Validação operacional da 7F

Concluída em 20/09/2026.

A 7F integrou a Missions Read API ao aplicativo público sem transferir autoridade de progresso, conclusão ou rewards para o cliente.

A implementação foi dividida em três passos:

- **7F1 — Client / Read Model:** cliente autenticado, presenter e React Query; commit `3a3c65c`;
- **7F2 — Public App Missions Panel:** painel integrado à tela de Conta; commit `b3393c8`;
- **7F3 — Real Android Validation:** validação ponta a ponta em dispositivo Android real.

A validação real confirmou:

- Samsung SM-M526B com Android 13;
- development client `com.rendaautomatica.app`;
- Metro acessado por `adb reverse` na porta 8081;
- Application API acessada por `adb reverse` na porta 8766;
- configuração e sessão existentes preservadas;
- painel `Missões da comunidade` renderizado na tela de Conta;
- resumo real com 1 missão concluída, 2 em andamento e 1 reward recebido;
- `community_primeira_aprovada` em 1/1, 100%, com 20 XP recebidos;
- `community_cinco_aprovadas` em 1/5, 20%, com 50 XP bloqueados;
- `community_dez_aprovadas` em 1/10, 10%, com 100 XP bloqueados;
- barras de progresso coerentes com os valores server-side;
- estados `granted` e `locked` apresentados corretamente;
- nenhum erro `ReactNativeJS`, `FATAL EXCEPTION`, `AndroidRuntime`, `TypeError`, `ReferenceError` ou exceção não tratada observado no smoke final.

### Validação operacional da 7G

Concluída em 20/09/2026.

A auditoria final da Etapa 7 confirmou:

- todos os contratos de Missions & Community Rewards V1 presentes e parseáveis;
- `MISSIONS_COMMUNITY_LIVE_REWARD_SETTLEMENT_ATIVO=true`;
- Application API com HTTP 200 e `status=ok`;
- `GET /api/v1/me/missions` protegido por sessão de usuário, retornando HTTP 401 sem sessão;
- `user_identity.sqlite3` com `integrity_check=ok`;
- zero erros de foreign key;
- 3 registros em `mission_progress`;
- 3 registros em `mission_progress_events`;
- 1 registro em `mission_reward_grants`;
- 1 reward `granted` e 0 rewards `pending`;
- test drift da 7F3 identificado e corrigido no commit `b34ff75`;
- 15/15 testes direcionados da Public App Missions aprovados;
- 180/180 testes finais de Missions, Gamification e superfícies relacionadas aprovados;
- TypeScript da Public App aprovado com `tsc --noEmit`;
- nenhum arquivo produtivo alterado durante a auditoria;
- arquivos locais persistentes de Expo e Mercado Livre preservados.

A Etapa 7 — Missions & Community Rewards V1 está operacionalmente concluída.

### Próxima macroetapa

**Etapa 8 — Community Reputation & Trust V1**

A Etapa 8 deve evoluir confiança e reputação comunitária sem alterar retroativamente as garantias estabelecidas pela Etapa 7.

---

## Etapa 8 — Community Reputation & Trust V1

**Status: EM EXECUÇÃO — 8A E 8B CONCLUÍDAS; 8C PRÓXIMA**

### Objetivo

Construir confiança mensurável em contribuições da comunidade.

### Escopo previsto

- reputação por contribuição;
- qualidade histórica;
- sinais confirmados e rejeitados;
- confiança do contribuidor;
- prevenção de manipulação;
- moderação;
- denúncia;
- auditoria;
- indicadores contextuais de contribuidor confiável;
- separação entre evidência objetiva, reputação social e opinião.

### Regra

Comentários, votos e reações podem gerar sinais auxiliares, mas não
substituem automaticamente evidência objetiva do marketplace.

### Subetapas

- **8A — Community Trust Model & Boundaries:** concluída.
- **8B — Community Trust Core Ledger:** concluída.
- **8C — Production Trust Policy & Anti-Abuse:** próxima.
- **8D — Community Discovery Wiring & Reconciliation:** planejada.
- **8E — Moderation & Reporting Foundation:** planejada.
- **8F — Trust Read API + Public App Surface:** planejada.
- **8G — Real Validation & Operational Close:** planejada.

### Arquitetura fechada na 8A

- Community Trust terá ledger autoritativo próprio;
- XP e nível permanecem em Gamification;
- `reputacao_total` fica reservado como projeção futura;
- `approved` pode gerar evidência positiva;
- `rejected` não gera penalidade automática;
- `motivo_status` precisa ser classificado antes de evidência negativa;
- rejeições técnicas ou sistêmicas são neutras por padrão;
- scoring numérico fica reservado para a 8C;
- Offer Scoring e Price Intelligence permanecem fora do Trust V1.

---
## Etapa 9 — Social / Competitive Layer V1

**Status: PLANEJADA — ESCOPO EXPANDIDO**

### Objetivo

Adicionar interação comunitária e competição sem transformar o Radar em
uma rede social genérica.

### Princípio

**O Radar é uma plataforma de ofertas com pessoas ao redor das ofertas.**

### Comentários em ofertas

- comentários vinculados a uma promoção;
- respostas a comentários;
- threads rasas e controladas;
- curtida ou marcação de comentário útil;
- edição e remoção do próprio comentário;
- denúncia;
- moderação;
- paginação;
- anti-spam;
- rate limiting.

### Interações da promoção

- gostei;
- acabou?;
- compartilhar;
- salvar;
- cupom expirado;
- oferta encerrada;
- preço alterado;
- disponibilidade;
- agregação server-side;
- mecanismos antiabuso.

### Perfil público opcional

Pode apresentar:

- avatar;
- nome público;
- nível;
- XP;
- badges;
- conquistas;
- missões;
- contribuições aprovadas;
- comentários úteis;
- reputação/trust;
- posição em rankings;
- controles de privacidade.

Stories, DMs, feed pessoal e follower graph não fazem parte do núcleo.

### Rankings

- ranking geral;
- ranking de XP;
- ranking de contribuições;
- ranking de missões/desafios;
- ranking por período;
- visualização da própria posição;
- privacidade;
- anti-farming;
- anti-Sybil.

### Gamificação visual

- badges;
- cards de conquistas;
- progresso;
- posição em ranking;
- marcos;
- celebrações discretas.

---

## Frente transversal — Public App Experience / Visual Polish

**Status: EVOLUÇÃO CONTÍNUA**

Esta frente evolui durante as demais etapas e não precisa esperar a Etapa 9.

### Oferta / promoção

- imagem real do produto;
- fallback sem imagem;
- cards de oferta mais ricos;
- imagem de destaque;
- marketplace;
- preço atual;
- preço anterior confiável;
- desconto;
- cupom;
- CTA principal;
- tags;
- histórico de preço;
- sinais de confiança.

### Feed e sistema visual

- melhor hierarquia;
- imagens;
- skeletons;
- placeholders;
- microinterações;
- tipografia;
- espaçamento;
- grid;
- iconografia;
- contraste;
- acessibilidade;
- dark mode consistente;
- componentes reutilizáveis;
- animações discretas;
- identidade visual própria.

### Perfil

- avatar;
- nível;
- XP;
- badges;
- missões;
- conquistas;
- estatísticas;
- ranking quando disponível;
- separação entre dados públicos e privados.

---
## Etapa 10 — Web / Extensão / Growth Surfaces

**Status: PLANEJADA**

### Objetivo

Expandir o mesmo backend para novas superfícies e canais de crescimento.

### Possíveis frentes

- aplicação web pública;
- extensão de navegador;
- páginas compartilháveis;
- ferramentas para criadores e afiliados;
- onboarding;
- aquisição;
- métricas de produto;
- experimentos de crescimento.

### Regra

Novas superfícies reutilizam contratos existentes. Regras de negócio não devem
ser copiadas para cada cliente.

---

# Frente paralela — Descoberta Comunitária

A Descoberta Comunitária já possui implementação própria e continua evoluindo
em paralelo ao roadmap principal de produto.

Ela fornece matéria-prima para futuras funcionalidades de:

- reputação;
- confiança;
- missões;
- recompensas;
- gamificação;
- comunidade.

Isso não antecipa o status das Etapas 6 a 9.

Uma contribuição comunitária continua sujeita às mesmas regras de validação,
identidade, preço, segurança e fail-closed do restante do sistema.

---

# Estado consolidado da Fase 2

| Etapa | Estado |
| --- | --- |
| 1. User-Facing API V1 | Concluída |
| 2. Public App MVP | Concluída como MVP |
| 3. Device Registration V1 | Concluída; token real validado |
| 4. Push Dispatcher V1 | Concluída; smoke real e receipt validados |
| 5. Personalized Feed V1 | Concluída; smoke real no Android validado |
| 6. Gamification & Reputation V1 | Concluída |
| 7. Missions & Community Rewards V1 | Concluída; 7A, 7B, 7C1, 7C2, 7D, 7E, 7F e 7G concluídas |
| 8. Community Reputation & Trust V1 | Em execução; 8A e 8B concluídas; 8C próxima |
| 9. Social / Competitive Layer V1 | Planejada; escopo expandido |
| 10. Web / Extensão / Growth Surfaces | Planejada |
| Public App Experience / Visual Polish | Frente transversal ativa |

---

# Proxima decisao de execucao

As Etapas 1 a 7 estao concluidas.

A próxima macroetapa de produto é:

**Etapa 8 - Community Reputation & Trust V1**

Fechamento da Etapa 7:

A 7D foi validada em produção em 20/09/2026:

- settlement core recoverable e idempotente;
- reconciliação de rewards pendentes no startup;
- primeiro reward real de 20 XP liquidado;
- Live Reward Settlement ativo no fluxo de aprovação;
- canário live idempotente aprovado;
- 0 rewards pendentes ao final;
- 0 XP duplicado;
- 0 eventos de Gamification duplicados;
- runtime e Chrome/CDP `HEALTHY`;
- SQLite íntegro e sem erros de foreign key.

A 7F foi concluída e validada no Android real, com a Missions Read API integrada à tela de Conta e sem transferir autoridade de XP, rewards ou estado das missões para o cliente.

A 7G concluiu a auditoria operacional da Etapa 7 com API saudável, boundary de sessão preservado, SQLite íntegro, 0 rewards pendentes, 180 testes aprovados e TypeScript aprovado.

A Etapa 7 — Missions & Community Rewards V1 está concluída.

A próxima macroetapa é:

**Etapa 8 — Community Reputation & Trust V1**

A camada social/competitiva continua reservada para a Etapa 9.
