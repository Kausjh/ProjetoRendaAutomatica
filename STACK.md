<!-- 63.8738, -149.7525 -->

# Stack Tecnológica

Este documento descreve a stack técnica atualmente utilizada pelo Projeto Renda Automática e o papel de cada componente no sistema.

A stack foi evoluindo junto com o projeto. O sistema deixou de ser apenas um conjunto de scrapers e passou a incluir coleta própria, Social Scout, persistência, validação por marketplace, observabilidade e supervisão operacional.

> Última referência funcional desta documentação: Social Scout V10.

---

## Visão geral

```text
Windows
  |
  +-- PowerShell / Task Scheduler
  |      |
  |      v
  |   Supervisor
  |      |
  |      +-- Runtime Python
  |      +-- Social Scout listener
  |      +-- Chrome / CDP quando necessário
  |
  v
Python
  |
  +-- Scrapers
  +-- Services
  +-- Repositories
  +-- Social Scout
  +-- Afiliados
  +-- Observabilidade
  +-- Publicação
```

---

## Linguagem principal

### Python

Python é a linguagem principal do projeto.

Ele é utilizado para:

- regras de negócio;
- scrapers;
- integrações;
- validação de produtos;
- Social Scout;
- persistência;
- geração de links de afiliado;
- histórico de preços;
- observabilidade;
- testes automatizados;
- rotinas de diagnóstico.

O projeto utiliza ambiente virtual local em `.venv`.

As dependências são instaladas e executadas dentro desse ambiente para reduzir interferência do Python global da máquina.

---

## Automação de navegador

### Playwright

Playwright é utilizado quando uma integração precisa observar uma página real carregada por navegador.

Ele permite:

- navegação em páginas dinâmicas;
- execução de JavaScript;
- acompanhamento de redirects;
- leitura de conteúdo renderizado;
- inspeção de JSON-LD;
- validação de páginas de produto;
- detecção de desafios humanos.

O navegador não é a primeira escolha para toda integração.

Quando uma API, feed ou requisição HTTP é suficiente e confiável, esses métodos são preferidos.

### Chrome DevTools Protocol

O projeto utiliza Chrome DevTools Protocol, ou CDP, para conectar serviços Python a uma instância dedicada de navegador.

O CDP é empregado em fluxos que precisam reaproveitar um navegador real ou executar validações de páginas específicas.

O uso de CDP é isolado das integrações que não precisam dele.

---

## Telegram

O projeto utiliza Telegram em dois papéis diferentes.

### Telegram Bot API

A Telegram Bot API é utilizada na camada de publicação e integrações de saída.

Ela permite que ofertas preparadas pelo pipeline sejam enviadas aos canais configurados.

### Telethon

Telethon é utilizado pelo Social Scout para acompanhar passivamente uma fonte Telegram autorizada.

O listener:

- recebe mensagens;
- extrai os dados necessários;
- persiste mensagens para processamento;
- não depende do bot de publicação;
- utiliza sessão local privada;
- não deve expor arquivos de sessão no repositório.

Arquivos de sessão são tratados como dados sensíveis.

---

## Social Scout

O Social Scout é uma camada de ingestão e validação de oportunidades externas.

A stack do Social Scout inclui:

- Telethon para listener;
- detector de promoções;
- processadores específicos por marketplace;
- resolutores de links;
- validadores de preço;
- SQLite para estado;
- fingerprints;
- retries;
- cooldowns;
- Shadow Mode;
- observabilidade agregada.

Na referência atual, o processador está na **V10**.

---

## HTTP e resolução de links

O projeto utiliza recursos HTTP para tarefas que não exigem navegador completo.

Dependendo da integração, podem ser usados:

- biblioteca padrão do Python;
- requisições HTTP;
- resolução de redirects;
- APIs oficiais;
- endpoints de afiliados;
- feeds de produtos.

A regra geral é utilizar o mecanismo mais simples que preserve identidade e confiabilidade.

---

## Dados estruturados

### JSON

JSON é usado em diferentes partes do projeto para:

- configuração;
- persistência leve;
- comunicação com APIs;
- dados de execução;
- resultados de serviços;
- arquivos de suporte.

### JSON-LD

JSON-LD é utilizado quando páginas de produto expõem dados estruturados confiáveis.

Na integração KaBuM!, por exemplo, JSON-LD pode fornecer:

- tipo `Product`;
- nome;
- ofertas;
- preço;
- moeda;
- disponibilidade.

A leitura de JSON-LD evita depender exclusivamente da aparência visual da página.

---

## Persistência

O projeto utiliza mais de um mecanismo de persistência.

### SQLite

SQLite é utilizado quando o sistema precisa de estado estruturado e consultável localmente.

Ele aparece em componentes como o Social Scout e sua observabilidade.

Vantagens:

- arquivo local;
- transações;
- consultas SQL;
- baixo overhead;
- boa adequação ao runtime atual.

### Arquivos estruturados

Arquivos JSON continuam sendo utilizados em componentes onde uma base relacional não é necessária.

Exemplos de responsabilidades que podem usar arquivos:

- histórico;
- registros locais;
- estado específico de integração;
- configurações não sensíveis.

A escolha entre SQLite e arquivo é feita por responsabilidade, não por uma regra única para todo o projeto.

---

## Afiliados

A camada de monetização trabalha com múltiplos programas e redes.

Entre as integrações e fluxos existentes estão:

- Mercado Livre;
- Shopee;
- Amazon;
- Awin.

A Awin é utilizada em integrações relacionadas a parceiros como KaBuM! e AliExpress.

O projeto mantém a lógica de afiliados separada da descoberta da oferta.

Uma oferta pode existir antes da transformação do link.

---

## Mercado Livre

A stack relacionada ao Mercado Livre inclui componentes para:

- descoberta;
- resolução de links;
- identificação de produto;
- classificação;
- validação;
- geração de link afiliado.

Parte do fluxo pode operar sem navegador, dependendo da etapa.

---

## Shopee

O Social Scout possui suporte específico para Shopee.

A implementação prioriza identidade exata e evita reintroduzir navegador quando ele não é necessário.

A resolução de múltiplos links é tratada de forma conservadora para impedir associação incorreta de produto.

---

## AliExpress

O AliExpress possui dois contextos técnicos.

### Coleta própria

A coleta nativa utiliza feeds de produto da Awin como fonte de candidatos.

A validação adicional pode envolver navegador e CDP.

### Social Scout

O Social Scout resolve links e exige destino compatível com produto real.

Páginas de coins, destinos genéricos, ambiguidades e indisponibilidades não são tratados automaticamente como ofertas válidas.

---

## KaBuM!

O suporte KaBuM! entrou no Social Scout V10.

A stack utilizada inclui:

- resolução de links `tidd.ly`;
- validação do host final;
- identidade exata por ID de produto;
- Playwright/CDP para PDP;
- leitura de JSON-LD;
- validação de preço BRL;
- detecção de desafio humano;
- cooldown persistente.

O domínio `tidd.ly` não é hardcoded como sinônimo de KaBuM!.

O destino precisa ser provado antes de o marketplace ser atribuído.

---

## Classificação e escopo

O projeto possui serviços responsáveis por classificar produtos e controlar o nicho permitido.

No Social Scout existe uma allowlist própria.

A classificação é complementada por proteções específicas quando necessário.

Um exemplo é o guard de CPU, criado para reduzir falsos positivos em produtos semanticamente chamados de “processador”, mas que não são hardware.

---

## Histórico de preços

O projeto possui repositório de histórico de preços.

Essa camada permite registrar observações ao longo do tempo e fornece base para:

- comparação futura;
- pontuação de ofertas;
- Price Intelligence;
- detecção de oportunidades reais.

---

## Pontuação

O projeto possui serviço de pontuação de ofertas.

A pontuação é separada da coleta.

Isso permite evoluir critérios sem reescrever o scraper.

---

## Observabilidade

A observabilidade do Social Scout utiliza dados persistidos e agregados.

O objetivo é responder perguntas operacionais sem expor conteúdo sensível.

Ela pode acompanhar métricas como:

- mensagens processadas;
- estados finais;
- erros transitórios;
- ofertas rejeitadas;
- candidatos de Shadow Mode;
- motivos de não resolução.

---

## Runtime

O projeto possui um runtime principal responsável por executar o pipeline de forma contínua.

Ele é separado do listener do Social Scout e do supervisor do Windows.

Essa separação permite recuperar um componente sem reiniciar toda a aplicação.

---

## Supervisor

O projeto utiliza um supervisor PowerShell versionado.

Responsabilidades:

- verificar componentes essenciais;
- iniciar componentes ausentes;
- recuperar o runtime após falhas;
- manter o ambiente local operacional.

O supervisor atua junto de uma tarefa agendada do Windows.

---

## Windows Task Scheduler

Uma tarefa agendada funciona como ponto de entrada para a infraestrutura local.

Ela inicia o supervisor, e o supervisor mantém os componentes necessários.

Esse desenho evita depender de abertura manual constante de terminais após reinicializações.

---

## PowerShell

PowerShell é utilizado para:

- operação local;
- instalação;
- diagnóstico;
- execução de testes;
- supervisão;
- tarefas de manutenção;
- automação no Windows.

Scripts permanentes importantes devem permanecer versionados no repositório.

---

## Testes

### Pytest

Pytest é o framework principal de testes.

Na validação completa da V10 do Social Scout, a suíte alcançou:

**562 testes aprovados.**

A suíte cobre, entre outros:

- scrapers;
- detector;
- processadores por marketplace;
- persistência;
- retries;
- escopo;
- validação de preço;
- wiring;
- regressões.

---

## Qualidade de código

### Black

Black é utilizado para formatação automática de Python.

### Ruff

Ruff é utilizado para análise estática e lint.

### pre-commit

pre-commit executa verificações antes de commits.

Entre os hooks utilizados no projeto estão verificações relacionadas a:

- Black;
- Ruff;
- fim de arquivo;
- whitespace;
- YAML;
- JSON;
- TOML;
- conflitos de merge;
- line endings;
- arquivos grandes.

---

## Controle de versão

### Git

Git é utilizado para versionamento local.

Mudanças relevantes são organizadas em commits específicos e revisáveis.

### GitHub

GitHub hospeda o repositório público.

O branch principal é `main`.

O repositório público deve permanecer livre de:

- segredos;
- sessões Telegram;
- bancos locais;
- perfis de navegador;
- dados privados de runtime.

---

## Configuração

### `.env`

Configurações locais e sensíveis ficam fora do código.

O `.env` real não deve ser versionado.

### `.env.example`

O `.env.example` documenta nomes de configurações que podem ser expostos publicamente.

Ele não deve conter:

- tokens reais;
- IDs privados;
- telefone;
- códigos de autenticação;
- sessão Telegram;
- credenciais de afiliado.

---

## Sistema operacional de desenvolvimento

O ambiente operacional atual é baseado em Windows.

A stack de operação local combina:

- Windows;
- PowerShell;
- Task Scheduler;
- Python virtual environment;
- Chrome dedicado;
- Git.

A arquitetura de domínio, porém, evita acoplar toda a lógica de negócio ao sistema operacional.

---

## Segurança operacional

Dados sensíveis devem permanecer fora do Git.

Entre os arquivos que exigem proteção estão:

- `.env`;
- credenciais;
- tokens;
- bancos locais;
- perfis de navegador;
- arquivos `*.session`;
- `*.session-journal`;
- `*.session-shm`;
- `*.session-wal`.

O Social Scout utiliza conta autorizada apenas como listener passivo.

---

## Resumo da stack

| Área | Tecnologia / abordagem |
|---|---|
| Linguagem | Python |
| Automação web | Playwright |
| Navegador | Chrome / Chromium |
| Comunicação com navegador | CDP |
| Listener Telegram | Telethon |
| Publicação Telegram | Telegram Bot API |
| Persistência estruturada | SQLite |
| Persistência leve | JSON |
| Afiliados | Mercado Livre, Shopee, Amazon, Awin |
| Feed de produtos | Awin |
| Testes | Pytest |
| Formatação | Black |
| Lint | Ruff |
| Hooks | pre-commit |
| Operação Windows | PowerShell |
| Inicialização | Windows Task Scheduler |
| Versionamento | Git |
| Repositório | GitHub |

---

## Estado da stack por componente

| Componente | Estado |
|---|---|
| Pipeline principal | Ativo |
| Social Scout | Ativo |
| Shadow Mode | Ativo |
| Mercado Livre Social Scout | Suportado |
| Shopee Social Scout | Suportado |
| AliExpress Social Scout | Suportado |
| KaBuM! Social Scout | Suportado desde V10 |
| Amazon Social Scout | Ainda não implementado |
| Observabilidade Social Scout | Ativa |
| Supervisor | Ativo |
| Autostart Windows | Ativo |
| Canonical Catalog | Roadmap |
| Alert Engine | Roadmap |
| API pública | Roadmap |
| App público | Roadmap |

---

## Direção futura

A stack atual foi construída para permitir a evolução para:

```text
Fontes
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

O objetivo é preservar a modularidade para que essas novas camadas sejam adicionadas sem transformar o projeto em um monólito rígido.

---

## Regra para atualizar este documento

`STACK.md` deve ser atualizado quando houver mudança relevante em:

- linguagem ou runtime;
- biblioteca principal;
- mecanismo de persistência;
- automação de navegador;
- infraestrutura operacional;
- testes;
- ferramentas de qualidade;
- integrações estruturais;
- componentes de produção.

Este arquivo não deve registrar segredos nem valores específicos de credenciais.
