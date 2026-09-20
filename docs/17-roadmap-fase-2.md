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

**Status: EM EXECUÇÃO — 7A, 7B E 7C1 CONCLUÍDAS; 7C2 EM IMPLEMENTAÇÃO**

### Objetivo

Transformar contribuições úteis em missões e recompensas verificáveis.

### Regras já fechadas

- progresso server-side;
- conclusão server-side;
- reward grant auditável;
- idempotência;
- apenas `community_discovery_approved` gera progresso;
- missões V1 lifetime;
- teto inicial de 170 XP;
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
- **7C2 — Controlled Runtime Activation:** em implementação.
- **7D — Reward Settlement to Gamification:** planejada.
- **7E — Missions Read API:** planejada.
- **7F — Public App Missions Surface:** planejada.
- **7G — Fechamento operacional:** planejada.

### Regra da 7C2

A reconciliação histórica deve terminar sem falhas antes do live wiring.

Falhas do Mission Engine não podem desfazer uma descoberta já persistida
como `approved`.

---
## Etapa 8 — Community Reputation & Trust V1

**Status: PLANEJADA**

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
| 7. Missions & Community Rewards V1 | Em execução; 7A, 7B e 7C1 concluídas; 7C2 em implementação |
| 8. Community Reputation & Trust V1 | Planejada |
| 9. Social / Competitive Layer V1 | Planejada; escopo expandido |
| 10. Web / Extensão / Growth Surfaces | Planejada |
| Public App Experience / Visual Polish | Frente transversal ativa |

---

# Proxima decisao de execucao

As Etapas 1 a 6 estao concluidas.

A proxima macroetapa de produto e:

**Etapa 7 - Missions & Community Rewards V1**

A Etapa 7 está em execução.

7A, 7B e 7C1 estão concluídas. A 7C2 prepara a ativação controlada
do Mission Engine no runtime real.

A próxima validação deve comprovar:

- criação das três tabelas `mission_*`;
- reconciliação da descoberta `approved` existente;
- três eventos criados na primeira reconciliação;
- três eventos idempotentes na segunda;
- um reward `pending` de 20 XP;
- gamification preservada em 140 XP, 7 eventos e reputação 0;
- live wiring somente depois da reconciliação bem-sucedida;
- settlement de XP desligado até a 7D.
