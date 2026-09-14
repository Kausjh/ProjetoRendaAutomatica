<!-- 63.8738, -149.7525 -->

# Projeto Renda Automática

Plataforma modular para **descoberta, validação, análise, monetização e distribuição de ofertas de tecnologia**.

O projeto começou como uma automação de links de afiliado e evoluiu para um motor que combina coleta própria, sinais externos, validação direta nos marketplaces, persistência, retries e controles de segurança.

> A prioridade não é publicar o maior número possível de ofertas.
>
> A prioridade é publicar menos, mas com evidência suficiente de identidade, preço e relevância.

---

## Estado atual

O projeto está em desenvolvimento ativo.

### Social Scout

- pipeline habilitado;
- processador atual: **V10**;
- **Shadow Mode** habilitado;
- listener Telegram passivo e autorizado;
- processamento persistente;
- fingerprints, cooldowns e TTL de retry;
- resolução específica por marketplace;
- validação de identidade e preço;
- allowlist de nicho;
- proteções fail-closed;
- observabilidade sem depender de payloads privados.

O Shadow Mode permite executar o fluxo real sem liberar automaticamente todas as decisões do Social Scout para publicação. A saída desse modo depende de evidência operacional suficiente.

### Qualidade

Na validação final da V10, a suíte chegou a **562 testes aprovados**.

Ferramentas de qualidade:

- Pytest
- Black
- Ruff
- pre-commit
- `git diff --check`

---

## Visão geral

```text
Fontes
  |
  +-- Coleta própria
  |
  +-- Social Scout
  |
  v
Detecção
  |
  v
Identificação do produto
  |
  v
Resolução do marketplace
  |
  v
Validação de identidade
  |
  v
Validação de preço
  |
  v
Classificação e escopo
  |
  v
Histórico / pontuação
  |
  v
Afiliados
  |
  v
Deduplicação / persistência
  |
  v
Publicação
```

A entidade central continua sendo a **Oferta**. Cada camada adiciona evidências e contexto antes de permitir que ela avance.

---

## Fontes de descoberta

### Coleta própria

Scrapers e integrações específicas procuram produtos diretamente nas fontes suportadas.

Dependendo do marketplace, uma integração pode usar:

- APIs;
- feeds de afiliados;
- HTTP;
- Playwright;
- Chrome DevTools Protocol;
- páginas de produto;
- JSON-LD e outros dados estruturados.

O projeto não força todos os marketplaces a usar a mesma estratégia.

### Social Scout

O Social Scout observa passivamente mensagens recebidas por uma conta Telegram autorizada e tenta transformar sinais externos em ofertas verificáveis.

A mensagem externa é tratada como uma **pista**, não como fonte absoluta de verdade.

```text
Mensagem
   |
   v
Detector
   |
   v
Oferta de produto?
   |
   v
Marketplace conhecido?
   |
   +-- sim --> processador específico
   |
   +-- não --> resolução conservadora quando suportada
                    |
                    v
             identidade exata
                    |
                    v
             validação real
```

Sempre que possível, identidade e preço são confrontados com a fonte oficial.

---

## Marketplaces

### Mercado Livre

O projeto possui integração para descoberta e processamento de ofertas do Mercado Livre.

No Social Scout, links podem ser resolvidos até o destino real antes da validação. O preço informado por uma fonte externa não é tratado automaticamente como preço oficial.

### Shopee

A Shopee possui processamento específico no Social Scout.

A identidade do produto é priorizada sobre inferências baseadas apenas em título. Mensagens com múltiplos links são tratadas de forma conservadora:

- repetições da mesma identidade podem ser aceitas;
- produtos diferentes geram ambiguidade;
- falhas de resolução podem permanecer transitórias;
- nenhum link é escolhido arbitrariamente só por aparecer primeiro.

A identificação não depende de navegador quando uma forma mais precisa e simples já é suficiente.

### AliExpress

O AliExpress aparece em dois fluxos.

#### Coleta própria

A coleta nativa pode usar feeds da Awin como fonte de candidatos e validar o produto depois.

O sistema reconhece condições como:

- indisponibilidade regional;
- preço não verificável;
- página inválida;
- desafio humano;
- falha transitória.

Condições conhecidas podem receber cache temporário para evitar tentativas repetitivas sem benefício.

#### Social Scout

Links curtos não são assumidos como produtos. O fluxo exige uma identidade real de item e rejeita destinos como:

- páginas de moedas;
- páginas genéricas;
- destinos sem ID de produto;
- destinos ambíguos;
- páginas indisponíveis.

### KaBuM!

O suporte à KaBuM! entrou no Social Scout na **V10**.

O domínio `tidd.ly` não é tratado como sinônimo de KaBuM!. Ele é apenas um redirecionador e o destino precisa ser provado.

```text
tidd.ly
   |
   v
redirect
   |
   v
destino final
   |
   v
host KaBuM?
   |
   v
URL de produto?
   |
   v
ID exato?
   |
   v
validação do PDP
```

A validação do PDP usa JSON-LD quando disponível para analisar:

- identidade;
- nome;
- moeda;
- preço;
- disponibilidade.

Ausência de disponibilidade explícita não significa automaticamente falta de estoque.

Quando a página apresenta desafio humano, o projeto **não tenta contorná-lo**. Um cooldown persistente reduz novas tentativas durante o período de proteção.

### Amazon

O projeto possui componentes relacionados à Amazon e monetização por afiliados.

O suporte Amazon dentro do Social Scout ainda não faz parte do fluxo atual.

---

## Filosofia fail-closed

O projeto prefere perder uma oportunidade a publicar uma informação errada.

```text
Marketplace não comprovado
→ não assume.

Dois produtos diferentes
→ ambiguidade.

Preço divergente
→ rejeição ou estado não verificável.

Cupom não confirmado
→ não declara como validado.

Produto fora do nicho
→ não segue.

Desafio humano
→ não tenta burlar.

Falha transitória
→ retry controlado.
```

A ausência de evidência não é tratada como evidência positiva.

---

## Escopo do Social Scout

O Social Scout possui uma allowlist própria.

Categorias atualmente aceitas:

- Armazenamento
- Computador e Mini PC
- Console
- Controle
- Fonte e energia
- Gabinete
- Iluminação de setup
- Kit upgrade
- Memória RAM
- Microfone
- Monitor
- Mouse e mousepad
- Notebook
- Placa de vídeo
- Placa-mãe
- Processador
- Realidade virtual
- Rede
- Refrigeração de PC
- Simulação
- Streaming e captura
- Suportes e conectividade
- Teclado
- Áudio

A expansão do escopo deve ser deliberada.

---

## Proteção contra falsos positivos

Classificação semântica isolada não é suficiente em todos os casos.

Durante o desenvolvimento, um produto de cozinha foi classificado semanticamente como **Processador**. A partir disso, a categoria recebeu uma verificação adicional de contexto de hardware.

A lógica procura evidências compatíveis com CPUs reais, como fabricantes, famílias, sockets e nomenclaturas técnicas.

---

## Preço, histórico e pontuação

O projeto diferencia conceitos como:

- preço informado pela fonte;
- preço oficial;
- preço original;
- preço promocional;
- preço com cupom;
- preço verificável;
- preço histórico.

Também existem componentes de histórico de preços e pontuação de ofertas.

Isso permite evoluir de uma lógica simples:

```text
"O preço está abaixo de X?"
```

para perguntas melhores:

```text
"Esse preço realmente está bom para este produto?"
```

Essa base prepara o caminho para **Price Intelligence**.

---

## Afiliados

A camada de afiliados mantém separadas informações como:

- link original;
- link de publicação;
- afiliador utilizado;
- transformação realizada ou não.

Uma falha de transformação não é registrada como sucesso.

O projeto possui fluxos relacionados a:

- Mercado Livre;
- Shopee;
- Amazon;
- Awin.

KaBuM! e AliExpress fazem parte das integrações relacionadas à Awin.

---

## Persistência, retry e deduplicação

O sistema não começa do zero a cada execução.

São persistidas informações relacionadas a:

- histórico de preços;
- publicações;
- Social Scout;
- estados de processamento;
- fingerprints;
- retries;
- deduplicação;
- observabilidade.

O Social Scout diferencia estados transitórios e terminais, aplica cooldowns e limita a janela de retry.

Mudanças relevantes no conteúdo podem produzir um novo fingerprint e permitir nova avaliação.

---

## Handoff durável

O pipeline possui mecanismos para reduzir perda de trabalho entre processamento e confirmação.

A intenção é manter uma semântica próxima de **at-least-once**, combinada com persistência e deduplicação para controlar repetições.

---

## Observabilidade

O projeto possui ferramentas de observabilidade para acompanhar agregados operacionais sem depender da exposição de mensagens privadas.

Exemplos:

- mensagens processadas;
- mensagens ignoradas;
- resoluções;
- preços rejeitados;
- estados não verificáveis;
- candidatos em Shadow Mode;
- erros transitórios.

---

## Operação automática

No ambiente Windows de desenvolvimento existe um supervisor responsável por manter componentes operacionais ativos.

```text
Supervisor
   |
   +-- Runtime principal
   |
   +-- Social Scout listener
   |
   +-- Chrome dedicado / CDP
```

Uma tarefa agendada do Windows atua como ponto de inicialização.

O supervisor pode recuperar componentes que deixam de executar.

---

## Arquitetura

```text
ProjetoRendaAutomatica/
|
+-- bots/
|   +-- integrações de saída
|
+-- config/
|   +-- configuração
|
+-- filters/
|   +-- filtragem
|
+-- formatters/
|   +-- apresentação
|
+-- models/
|   +-- domínio
|
+-- repositories/
|   +-- persistência
|
+-- scrapers/
|   +-- descoberta
|
+-- services/
|   +-- regras de negócio
|   +-- validações
|   +-- afiliados
|   +-- Social Scout
|
+-- tests/
|   +-- testes automatizados
|
+-- docs/
|   +-- documentação técnica
|
+-- main.py
+-- runtime.py
+-- pyproject.toml
+-- README.md
+-- .env.example
```

Princípios buscados:

- responsabilidade única;
- baixo acoplamento;
- alta coesão;
- testabilidade;
- extensibilidade;
- evolução incremental.

Para detalhes, consulte `ARCHITECTURE.md`.

---

## Tecnologias principais

- Python
- Playwright
- Telethon
- Telegram Bot API
- SQLite
- JSON
- Awin
- Pytest
- Black
- Ruff
- pre-commit
- Git
- GitHub
- PowerShell

---

## Configuração e segurança

Configurações locais e segredos não devem ficar no código.

O projeto usa `.env` para valores específicos de ambiente e mantém `.env.example` como referência pública.

O repositório público não deve conter:

- credenciais;
- tokens;
- códigos de autenticação;
- sessões Telegram;
- bancos locais de produção;
- perfis de navegador;
- payloads privados;
- identificadores privados desnecessários.

Arquivos sensíveis de runtime são protegidos por `.gitignore`.

---

## Documentação

Arquivos importantes:

- `ARCHITECTURE.md`
- `STACK.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `docs/`

A documentação deve evoluir junto com o código.

---

## Roadmap

A direção de longo prazo é transformar o motor atual em uma plataforma própria de inteligência de compras.

```text
Social Scout + Scrapers
          |
          v
   Canonical Catalog
          |
          v
   Price Intelligence
          |
          v
     Alert Engine
          |
          v
         API
          |
          v
   App / Web / Extensão
```

### Canonical Catalog

A meta é criar uma identidade própria para cada produto, independente do marketplace.

```text
AMD Ryzen 7 5700X
|
+-- Mercado Livre
+-- Shopee
+-- KaBuM!
+-- AliExpress
+-- Amazon
```

O anúncio deixa de ser a identidade principal. O produto passa a ser.

### Price Intelligence

Evoluções planejadas:

- histórico consolidado;
- comparação entre marketplaces;
- referência de preço normal;
- detecção de quedas relevantes;
- preço final;
- análise de oportunidade real.

### Alert Engine

Exemplos de regras futuras:

```text
"Avise quando uma RTX atingir determinado preço."
```

```text
"Avise quando este produto estiver abaixo da média histórica."
```

### Plataforma pública

Etapas futuras podem incluir:

- API própria;
- contas de usuários;
- preferências;
- watchlists;
- notificações push;
- feed personalizado;
- app;
- interface web;
- extensão de navegador;
- ferramentas para criadores e parceiros.

---

## Princípios do projeto

Antes de adicionar uma funcionalidade:

1. A qual camada ela pertence?
2. Ela aumenta desnecessariamente o acoplamento?
3. Existe identidade verificável para o dado?
4. Estamos assumindo algo que poderíamos validar?
5. O comportamento falha de forma segura?
6. A funcionalidade pode ser testada?
7. A documentação precisa ser atualizada?

---

## Filosofia

O Projeto Renda Automática não é apenas um scraper.

Ele está sendo construído como uma plataforma para:

**descobrir → verificar → analisar → monetizar → distribuir**

oportunidades comerciais de forma automatizada.

---

## Contribuindo

Consulte `CONTRIBUTING.md` antes de propor alterações estruturais.

---

## Licença

Distribuído sob licença MIT.

Consulte `LICENSE`.

---

## Autor

**Kauê Jhonatas**

Projeto desenvolvido com foco em automação comercial, engenharia de software, inteligência de preços e arquitetura modular.

## Contrato de clientes da API V1

A API de aplicação possui contrato público e versionado em
`contracts/api_v1.contract.json`. O contrato descreve as cinco operações
read-only de `/api/v1`, paginação, autenticação e códigos de erro esperados.

O cliente Python em `clients/reference_api_v1.py` é apenas uma implementação
de referência para testes, automações e validação de compatibilidade. Ele não
é o aplicativo final.

O aplicativo Android privado deve permanecer fora deste repositório público.
Ele deve consumir o mesmo contrato V1, sem copiar regras de negócio, lógica de
curadoria, credenciais administrativas ou artefatos privados para este
repositório.

## Política de acesso seguro de clientes V1

Além do contrato `/api/v1`, o repositório mantém
`contracts/client_access_policy_v1.json` e
`docs/11-acesso-clientes.md`.

O cliente de referência aplica a política por padrão: loopback HTTP é aceito,
acesso remoto por HTTPS exige Bearer token e HTTP remoto exige token mais uma
declaração explícita de transporte criptografado/confiável externo. A API
administrativa da porta `8765` não faz parte do contrato de clientes.

<!-- bloco26-client-transport-v1:start -->
### Client Transport V1 — Tailscale TCP

O cliente remoto da Application API usa um transporte privado sobre a tailnet:

`cliente -> Tailscale IPv4:18767 -> TCP forwarder -> 127.0.0.1:8766`

Regras do transporte:

- a Application API continua vinculada ao loopback (`127.0.0.1:8766`);
- o acesso remoto exige Bearer token;
- o tráfego remoto depende de uma tailnet autenticada e criptografada;
- MagicDNS não é requisito do cliente;
- Tailscale Funnel não faz parte da arquitetura;
- não há exposição da Application API à Internet pública;
- a API administrativa (`8765`) não faz parte do contrato de transporte do cliente;
- o aplicativo Android privado permanece fora deste repositório.

Contrato legível por máquina: `contracts/client_transport_v1.json`.

Documentação operacional: `docs/12-transporte-cliente-tailscale.md`.
<!-- bloco26-client-transport-v1:end -->

<!-- bloco27-user-identity-v1:start -->
### User Identity Foundation V1

O Bloco 27 introduz a fundação persistente de contas e sessões para a futura
plataforma pública.

A identidade de usuário é deliberadamente separada do Bearer de
infraestrutura da Application API e do control plane administrativo.

Nesta fase não são criadas novas rotas HTTP: `/api/v1` continua read-only.
A camada fornece hashing de senha com `scrypt`, salt individual, sessões
aleatórias, persistência somente do hash do token, expiração e revogação.

Contrato: `contracts/user_identity_v1.json`.

Documentação: `docs/13-identidade-usuarios.md`.
<!-- bloco27-user-identity-v1:end -->

<!-- bloco28-user-personalization-v1:start -->
### User Personalization & Watchlists V1

O Bloco 28 adiciona preferências persistentes e watchlists por conta sobre a
fundação de identidade do Bloco 27.

As preferências V1 controlam notificações de preço e marketplaces preferidos.
As watchlists acompanham produtos por `canonical_key`, com preço alvo opcional
persistido em centavos e configuração para futura notificação de queda.

Nesta fase não são criadas novas rotas HTTP e não existe entrega de alertas
personalizados. A Application API V1 permanece read-only.

Contrato: `contracts/user_personalization_v1.json`.

Documentação: `docs/14-personalizacao-watchlists.md`.
<!-- bloco28-user-personalization-v1:end -->

<!-- bloco29-personalized-alert-matching-v1:start -->
### Personalized Alert Matching V1

O Bloco 29 conecta eventos de preço às watchlists e preferências de usuários.

O matching considera `canonical_key`, notificações habilitadas, marketplaces
preferidos, preço alvo e evidência direcional de queda. As correspondências
são persistidas e deduplicadas por evento + item de watchlist.

Nesta fase não existe entrega: sem push, email, Telegram ou novas rotas HTTP.
A Application API V1 permanece read-only.

Contrato: `contracts/personalized_alert_matching_v1.json`.

Documentação: `docs/15-alertas-personalizados-matching.md`.
<!-- bloco29-personalized-alert-matching-v1:end -->

<!-- bloco30-personalized-notification-outbox-v1:start -->
### Personalized Notification Outbox V1

O Bloco 30 adiciona a fundação persistente de entrega para os matches
personalizados do Bloco 29.

Cada match pode originar uma intenção idempotente de canal `push`, mantida em
outbox com estados `pending`, `processing`, `delivered` e `failed`, contador de
tentativas e suporte a retry com disponibilidade futura.

Esta fase é push-ready, mas não envia push real: não há provedor configurado,
tokens de dispositivo, credenciais externas ou novas rotas HTTP. A Application
API V1 permanece read-only.

Contrato: `contracts/personalized_notification_outbox_v1.json`.

Documentação: `docs/16-notification-outbox.md`.
<!-- bloco30-personalized-notification-outbox-v1:end -->

<!-- fase2-roadmap:start -->
## Roadmap — Fase 2

A Fase 1 foi concluída com 30/30 blocos.

A Fase 2 transforma a infraestrutura construída em produto utilizável por
usuários finais.

Ordem oficial:

1. User-Facing API V1
2. Public App MVP
3. Device Registration V1
4. Push Dispatcher V1
5. Personalized Feed V1
6. Web / Extensão / Growth Surfaces

O primeiro passo é estabilizar o contrato e a fronteira de autenticação da
User-Facing API antes de abrir novas rotas.

Documentação completa: `docs/17-roadmap-fase-2.md`.
<!-- fase2-roadmap:end -->

<!-- fase2-user-facing-auth-contract-v1:start -->
### Fase 2 — User-Facing API V1: Auth Contract

A fronteira de autenticação da User-Facing API usa duas camadas independentes:

- `Authorization: Bearer <API_APLICACAO_TOKEN>` protege o acesso à
  infraestrutura conforme a política de transporte existente;
- `X-User-Session: pra_usr_v1_<token>` identifica a sessão do usuário final.

O Bearer de infraestrutura nunca representa uma conta e a sessão do usuário
nunca substitui a proteção de infraestrutura.

Este estágio formaliza somente o contrato; as novas rotas ainda não são
implementadas.

Contrato: `contracts/user_facing_api_auth_v1.json`.

Documentação: `docs/18-user-facing-api-auth-v1.md`.
<!-- fase2-user-facing-auth-contract-v1:end -->

<!-- fase2-user-facing-http-foundation-v1:start -->
### Fase 2 — User-Facing API V1: HTTP Foundation

A infraestrutura HTTP compartilhada da superfície user-facing está preparada
sem alterar as rotas de negócio existentes.

Ela fornece parsing JSON com limite de payload, envelopes de sucesso/erro,
extração de `X-User-Session` e resolução server-side da sessão do usuário.

`ServidorApiAplicacao` aceita opcionalmente o serviço de identidade, preservando
compatibilidade com o runtime atual enquanto `register/login` ainda não foram
abertos.

Contrato: `contracts/user_facing_api_http_foundation_v1.json`.

Documentação: `docs/19-user-facing-api-http-foundation-v1.md`.
<!-- fase2-user-facing-http-foundation-v1:end -->

<!-- fase2-user-facing-register-login-v1:start -->
### Fase 2 — User-Facing API V1: Register/Login

As primeiras rotas HTTP de usuário estão disponíveis:

- `POST /api/v1/auth/register`;
- `POST /api/v1/auth/login`.

O cadastro cria uma conta sem abrir sessão automaticamente. O login retorna uma
sessão opaca `pra_usr_v1_...`, usando a fundação de identidade existente.

O runtime injeta `UserIdentityService` na Application API usando
`database/user_identity.sqlite3`.

A proteção de infraestrutura continua separada da identidade do usuário.

Contrato: `contracts/user_facing_api_register_login_v1.json`.

Documentação: `docs/20-user-facing-api-register-login-v1.md`.
<!-- fase2-user-facing-register-login-v1:end -->

<!-- fase2-user-facing-logout-me-v1:start -->
### Fase 2 — User-Facing API V1: Logout + Me

As primeiras rotas autenticadas por sessão de usuário estão disponíveis:

- `POST /api/v1/auth/logout`;
- `GET /api/v1/me`.

`/me` deriva a conta exclusivamente de `X-User-Session`; `conta_id` enviado pelo
cliente não seleciona identidade. O logout revoga somente a sessão atual e
preserva outras sessões válidas da mesma conta.

A camada `Authorization: Bearer <API_APLICACAO_TOKEN>` continua independente e
preservada quando configurada.

Contrato: `contracts/user_facing_api_logout_me_v1.json`.

Documentação: `docs/21-user-facing-api-logout-me-v1.md`.
<!-- fase2-user-facing-logout-me-v1:end -->

<!-- fase2-user-facing-preferences-v1:start -->
### Fase 2 — User-Facing API V1: Preferences HTTP

Preferências autenticadas estão disponíveis em:

- `GET /api/v1/me/preferences`;
- `PATCH /api/v1/me/preferences`.

O PATCH é parcial: campos omitidos preservam o valor atual. A conta é derivada
somente de `X-User-Session`, e `conta_id` enviado pelo cliente não é aceito.

O runtime injeta `UserPersonalizationService` usando o mesmo
`database/user_identity.sqlite3` da identidade.

A watchlist continua fora da API HTTP neste subbloco.

Contrato: `contracts/user_facing_api_preferences_v1.json`.

Documentação: `docs/22-user-facing-api-preferences-v1.md`.
<!-- fase2-user-facing-preferences-v1:end -->

<!-- fase2-user-facing-watchlist-v1:start -->
### Fase 2 — User-Facing API V1: Watchlist HTTP

A watchlist autenticada está disponível em:

- `GET /api/v1/me/watchlist`;
- `PUT /api/v1/me/watchlist/{canonical_key}`;
- `DELETE /api/v1/me/watchlist/{canonical_key}`.

A identidade vem somente de `X-User-Session`. `conta_id`, `canonical_key` no
body e ids internos não são aceitos como override.

`preco_alvo` é retornado como string decimal ou `null`.

Contrato: `contracts/user_facing_api_watchlist_v1.json`.

Documentação: `docs/23-user-facing-api-watchlist-v1.md`.
<!-- fase2-user-facing-watchlist-v1:end -->

<!-- fase2-user-facing-abuse-controls-v1:start -->
### Fase 2 — User-Facing API V1: Abuse Controls

`register` e `login` agora possuem rate limiting V1 em memória, thread-safe e
sem dependência externa.

Quando o limite é atingido, a API responde `429` com `Retry-After`.

Defaults e variáveis de ambiente estão documentados em
`docs/24-user-facing-api-abuse-controls-v1.md`.

Contrato: `contracts/user_facing_api_abuse_controls_v1.json`.
<!-- fase2-user-facing-abuse-controls-v1:end -->

<!-- fase2-public-app-mvp-architecture-v1:start -->
### Fase 2 — Public App MVP: arquitetura V1

O aplicativo de usuário final será construído para Android com **React Native + Expo + TypeScript**.

O código público do app poderá viver em `apps/public-mobile/`. O aplicativo
Android privado de administração continua fora deste repositório.

O MVP inicial opera como alpha sobre o transporte Tailscale já existente
(`:18767 -> 127.0.0.1:8766`) e nunca usa a API administrativa `8765`.

Nenhum `API_APLICACAO_TOKEN` será hardcoded, commitado ou embutido como segredo
fixo no app. A sessão de usuário será armazenada em Secure Store.

Contrato: `contracts/public_app_mvp_architecture_v1.json`.

Documentação: `docs/25-public-app-mvp-architecture.md`.
<!-- fase2-public-app-mvp-architecture-v1:end -->

<!-- fase2-public-app-mvp-bootstrap-v1:start -->
### Fase 2 — Public App MVP: Bootstrap V1

O primeiro código do app público Android vive em `apps/public-mobile/`.

Bootstrap ativo:

- React Native + Expo;
- Expo Router;
- TypeScript estrito;
- TanStack Query;
- Expo Secure Store.

Nenhum segredo de infraestrutura é embutido no app. O próximo bloco implementa
o API client e a abstração efetiva de transporte.

Contrato: `contracts/public_app_mvp_bootstrap_v1.json`.

Documentação: `docs/26-public-app-mvp-bootstrap-v1.md`.
<!-- fase2-public-app-mvp-bootstrap-v1:end -->

<!-- fase2-public-app-api-client-transport-v1:start -->
### Fase 2 — Public App MVP: API Client / Transport V1

O app público possui uma camada HTTP própria em `apps/public-mobile/src/api/`.

A camada separa:

- Bearer de infraestrutura;
- sessão `X-User-Session`;
- respostas read-only em JSON bruto;
- envelopes da User-Facing API;
- timeout, falha de rede e `Retry-After`.

A UI não conhece Tailscale, IP, porta ou headers de autenticação.

Contrato: `contracts/public_app_api_client_transport_v1.json`.

Documentação: `docs/27-public-app-api-client-transport-v1.md`.
<!-- fase2-public-app-api-client-transport-v1:end -->

<!-- fase2-public-app-auth-session-v1:start -->
### Fase 2 — Public App MVP: Auth Session V1

O app público possui estado real de autenticação em
`apps/public-mobile/src/auth/`.

O provider restaura a sessão do Secure Store ao abrir o app, valida `/me`,
persiste a sessão após login e garante limpeza local no logout. Sessões
rejeitadas com `401` são removidas; falhas transitórias de rede não provocam
logout automático.

O root layout já inicializa esse estado para preparar o roteamento autenticado.

Contrato: `contracts/public_app_auth_session_v1.json`.

Documentação: `docs/28-public-app-auth-session-v1.md`.
<!-- fase2-public-app-auth-session-v1:end -->

<!-- fase2-public-app-auth-ui-v1:start -->
### Fase 2 — Public App MVP: Auth UI V1

O fluxo de autenticação do app público agora possui telas utilizáveis:

- gate inicial;
- configuração local do alpha;
- login;
- cadastro;
- home protegida;
- logout.

Endpoint e Bearer continuam exclusivamente locais e não são embutidos no
aplicativo. A home autenticada ainda é apenas a entrada para os próximos
recursos do MVP.

Contrato: `contracts/public_app_auth_ui_v1.json`.

Documentação: `docs/29-public-app-auth-ui-v1.md`.
<!-- fase2-public-app-auth-ui-v1:end -->

<!-- fase2-public-app-offers-v1:start -->
### Fase 2 — Public App MVP: Offers V1

O app público agora consome o catálogo read-only real:

- lista de produtos;
- detalhe por chave canônica;
- histórico de preço;
- retry;
- pull-to-refresh;
- estados de loading, erro e lista vazia.

A UI passa por uma camada de apresentação em `src/offers/`, sem se acoplar
diretamente ao JSON bruto do backend.

Contrato: `contracts/public_app_offers_v1.json`.

Documentação: `docs/30-public-app-offers-v1.md`.
<!-- fase2-public-app-offers-v1:end -->
