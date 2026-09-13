# Roadmap — Fase 2

## Status da transição

A Fase 1 foi concluída com o roadmap 30/30.

O backend já possui coleta, catálogo canônico, inteligência de preços,
Promotion/Opportunity Intelligence, Alert Engine, Application API V1,
fundação de identidade, preferências, watchlists, matching personalizado e
outbox persistente de notificações.

A Fase 2 transforma essa infraestrutura em uma superfície utilizável por um
usuário final.

## Princípio da Fase 2

A ordem é deliberadamente:

1. estabilizar contrato e autenticação de usuário;
2. expor capacidades já existentes;
3. construir o cliente público mínimo;
4. registrar dispositivos;
5. ativar push real;
6. expandir o produto com feed e novas superfícies.

Não começar pelo push e não começar por um app completo evita colocar uma
interface sobre contratos ainda instáveis.

---

## Etapa 1 — User-Facing API V1

### Objetivo

Expor de forma segura as capacidades de usuário que já existem internamente.

### Escopo

- contrato público versionado para identidade de usuário;
- fronteira explícita entre credencial de infraestrutura e sessão de usuário;
- cadastro de conta;
- login;
- logout/revogação de sessão;
- leitura do usuário autenticado;
- leitura e atualização de preferências;
- leitura, adição, atualização e remoção de watchlist;
- erros e respostas versionados;
- rate limiting e proteção contra abuso onde aplicável;
- testes de autorização entre usuários;
- Application API pública sem acoplamento ao control plane administrativo.

### Gate arquitetural obrigatório

Antes de abrir rotas, definir como coexistem:

- proteção de infraestrutura/transporte;
- autenticação da sessão do usuário.

O Bearer de infraestrutura não pode virar identidade de usuário e o token de
sessão não deve ser confundido com uma credencial operacional.

### Critério de conclusão

Um cliente de referência deve conseguir criar uma conta, autenticar, consultar
o próprio perfil, alterar preferências e administrar a própria watchlist sem
acessar dados de outro usuário.

---

## Etapa 2 — Public App MVP

### Objetivo

Criar o primeiro cliente público utilizável.

### Escopo mínimo

- login/cadastro;
- sessão persistente;
- busca/consulta de produtos disponibilizados pela API;
- tela de produto;
- watchlist;
- preço alvo;
- preferências básicas;
- estado de carregamento e erros;
- nenhum segredo de infraestrutura embutido no app.

### Boundary

O aplicativo Android privado de administração continua sendo outro produto e
permanece fora do repositório público.

### Critério de conclusão

Um usuário consegue instalar o MVP, autenticar-se e administrar sua watchlist
usando somente contratos públicos.

---

## Etapa 3 — Device Registration V1

### Objetivo

Associar instalações do app público a uma conta para permitir notificações
push.

### Escopo

- modelo de dispositivo;
- registro e revogação de token;
- múltiplos dispositivos por conta;
- rotação de token;
- estado ativo/inativo;
- proteção de acesso por usuário;
- nenhuma credencial de provedor exposta ao cliente.

### Critério de conclusão

O backend consegue saber quais dispositivos ativos pertencem a uma conta,
sem enviar push ainda.

---

## Etapa 4 — Push Dispatcher V1

### Objetivo

Conectar a outbox persistente do Bloco 30 a um provedor real de push.

### Escopo

- adapter de provedor;
- credenciais fora do código-fonte;
- consumo seguro da outbox;
- envio para dispositivos ativos;
- sucesso -> delivered;
- falha recuperável -> retry;
- token inválido -> tratamento/revogação;
- falha terminal -> failed;
- idempotência;
- observabilidade;
- limites e backoff.

### Critério de conclusão

Um match elegível consegue virar uma notificação real no dispositivo correto,
com retry e deduplicação preservados.

---

## Etapa 5 — Personalized Feed V1

### Objetivo

Transformar os mesmos sinais personalizados em uma experiência consultável,
não somente em notificações.

### Escopo

- feed por usuário;
- ordenação por relevância/recência;
- produtos da watchlist;
- oportunidades compatíveis com preferências;
- paginação;
- deduplicação;
- contrato público versionado.

### Critério de conclusão

O usuário autenticado consegue abrir o app e ver um feed personalizado sem
depender de uma notificação push.

---

## Etapa 6 — Web, Extensão e Growth Surfaces

### Objetivo

Expandir o mesmo backend para novas superfícies.

### Possíveis frentes

- interface web pública;
- extensão de navegador;
- ferramentas para criadores/afiliados;
- páginas compartilháveis de produto;
- onboarding e aquisição;
- métricas de produto;
- experimentos de crescimento.

### Regra

Essas superfícies reutilizam contratos existentes. Regras de negócio não
devem ser copiadas para cada cliente.

---

## Estado atual antes da Fase 2

### Operacional ou comprovado neste review

- Application API V1 saudável;
- scrapers/pipeline;
- Social Scout/Partner Scout conforme componentes existentes;
- catálogo canônico;
- inteligência de preços;
- Promotion/Opportunity Intelligence;
- Alert Engine;
- transporte privado de cliente;
- observabilidade/supervisão presentes no repositório.

O control plane administrativo está implementado, porém sua disponibilidade
de runtime não foi confirmada no review pós-roadmap e deve ser verificada
separadamente antes de qualquer manutenção operacional nele.

### Implementado internamente, ainda sem superfície pública de usuário

- contas e sessões;
- preferências;
- watchlists;
- matching personalizado;
- outbox persistente de notificações.

### Preparado, ainda não real

- cadastro/login via API pública;
- mutações de preferências/watchlists pela API pública;
- registro de dispositivos;
- push real;
- feed personalizado;
- app público;
- web pública;
- extensão de navegador.

---

## Próximo passo

Iniciar a Etapa 1 da Fase 2:

**User-Facing API V1**

Primeiro subpasso:

**formalizar o contrato e a fronteira de autenticação antes de criar rotas.**
