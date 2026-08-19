# Arquitetura

## Objetivo

Este documento define a arquitetura oficial do Projeto Renda Automática.

Seu objetivo é servir como referência para qualquer desenvolvedor que venha a trabalhar no projeto, explicando como o sistema está organizado, quais são as responsabilidades de cada camada e quais princípios devem ser respeitados durante sua evolução.

Este documento descreve apenas a arquitetura do sistema. Detalhes de implementação, instalação e tecnologias utilizadas são documentados em arquivos específicos da pasta `docs`.

---

# Visão Geral

O Projeto Renda Automática é uma plataforma de automação responsável por coletar ofertas em diferentes fontes, processá-las, aplicar regras de negócio e publicá-las automaticamente em canais previamente configurados.

A arquitetura foi projetada para permitir crescimento contínuo sem necessidade de alterações estruturais. Novos scrapers, filtros, canais de publicação e mecanismos de armazenamento podem ser adicionados mantendo a mesma organização do sistema.

Os principais objetivos da arquitetura são:

- modularidade;
- baixo acoplamento;
- alta coesão;
- facilidade de manutenção;
- facilidade de testes;
- escalabilidade;
- reutilização de código.

---

# Fluxo Geral

```text
Internet
    │
    ▼
Scrapers
    │
    ▼
Normalização
    │
    ▼
Models
    │
    ▼
Filters
    │
    ▼
Services
    │
    ▼
Repositories
    │
    ▼
Bots
    │
    ▼
Telegram
```

Cada etapa possui apenas uma responsabilidade e deve executar somente aquilo que lhe compete.

---

# Organização das Camadas

## Scrapers

São responsáveis exclusivamente pela coleta de informações.

Seu trabalho consiste em acessar uma fonte de dados, extrair as informações necessárias e transformá-las em objetos utilizados pelo sistema.

### Devem

- acessar páginas HTML;
- consumir APIs;
- utilizar Playwright;
- utilizar Requests;
- interpretar dados da fonte.

### Nunca devem

- publicar mensagens;
- salvar dados permanentemente;
- decidir se uma oferta é boa;
- aplicar regras de negócio;
- calcular pontuação;
- conhecer Telegram;
- conhecer banco de dados.

---

## Models

Representam as entidades do domínio.

Atualmente o principal modelo é a Oferta.

No futuro poderão existir outros modelos como:

- Produto;
- Loja;
- Categoria;
- Marca;
- Histórico.

Models representam apenas dados.

Eles não devem conter lógica de negócio nem comunicação externa.

---

## Filters

Responsáveis por validar critérios objetivos.

Exemplos:

- preço máximo;
- desconto mínimo;
- categoria permitida;
- loja bloqueada;
- palavras proibidas.

Cada filtro deve possuir apenas uma responsabilidade.

Filtros não devem conhecer outros filtros.

---

## Services

Services concentram toda a inteligência do sistema.

Toda decisão sobre uma oferta deve acontecer nesta camada.

Exemplos:

- calcular pontuação;
- validar regras;
- decidir aprovação;
- orquestrar o pipeline;
- coordenar chamadas entre módulos.

Services nunca devem realizar scraping diretamente.

---

## Repositories

Responsáveis exclusivamente pela persistência dos dados.

Hoje:

- `publicados.json`

Futuramente:

- SQLite;
- PostgreSQL;
- Redis.

Repositories armazenam e recuperam dados.

Eles nunca devem executar regras de negócio.

---

## Bots

São responsáveis pela comunicação com serviços externos.

Hoje:

- Telegram.

Futuramente:

- Discord;
- WhatsApp;
- X;
- Email;
- APIs próprias.

Bots recebem uma oferta pronta para publicação.

Eles nunca devem decidir se uma oferta deve ou não ser publicada.

---

# Responsabilidades das Camadas

| Camada | Responsabilidade Principal |
|---------|----------------------------|
| Scrapers | Coletar dados |
| Models | Representar entidades |
| Filters | Aplicar critérios objetivos |
| Services | Executar regras de negócio |
| Repositories | Persistir informações |
| Bots | Publicar conteúdo |

Caso uma funcionalidade pareça pertencer a mais de uma camada, ela provavelmente deve ser dividida.

---

# Dependências Permitidas

A direção das dependências deve permanecer sempre a mesma.

```text
Scrapers
     │
     ▼
Models

Filters
     │
     ▼
Models

Services
     │
     ├────────► Models
     ├────────► Filters
     └────────► Repositories

Repositories
     │
     ▼
Models

Bots
     │
     ▼
Models
```

Essa organização reduz o acoplamento entre módulos e facilita futuras substituições.

---

# Dependências Proibidas

As seguintes situações são consideradas violações da arquitetura:

- Scraper publicar mensagens.
- Scraper acessar banco de dados.
- Scraper aplicar regras de negócio.
- Model acessar internet.
- Model executar scraping.
- Filter salvar arquivos.
- Filter acessar banco.
- Repository calcular pontuação.
- Repository aplicar filtros.
- Bot decidir aprovação de ofertas.
- Bot modificar regras de negócio.

Sempre que uma dessas situações surgir durante o desenvolvimento, a implementação deverá ser revista.

---

# Princípios Arquiteturais

O projeto adota os seguintes princípios.

## Responsabilidade Única

Cada módulo deve possuir apenas um motivo para sofrer alterações.

---

## Baixo Acoplamento

As camadas devem conhecer o mínimo possível umas das outras.

---

## Alta Coesão

Cada diretório deve conter funcionalidades relacionadas ao mesmo contexto.

---

## Composição

Sempre que possível deve-se preferir composição em vez de herança.

---

## Configuração Centralizada

Configurações devem permanecer concentradas em módulos específicos.

---

## Extensibilidade

Adicionar novos módulos não deve exigir alterações estruturais no restante do sistema.

---

# Regra para Expansão

Adicionar um novo scraper deve exigir apenas:

1. criar a classe;
2. herdar de `BaseScraper`;
3. registrá-la no coletor.

Nenhuma alteração adicional deverá ser necessária.

O mesmo princípio vale para novos filtros, novos repositories e novos bots.

---

# Objetivos Arquiteturais

A arquitetura foi planejada para suportar:

- dezenas de scrapers;
- múltiplos canais de publicação;
- múltiplos bancos de dados;
- múltiplos países;
- múltiplos idiomas;
- sistema de plugins;
- processamento paralelo;
- filas de tarefas;
- cache distribuído.

A expansão deve ocorrer por adição de módulos, nunca por reestruturação completa da arquitetura.

---

# Glossário

## Oferta

Objeto contendo todas as informações necessárias para representar um produto encontrado durante o scraping.

---

## Scraper

Componente responsável por coletar informações de uma fonte.

---

## Pipeline

Sequência de etapas percorridas por uma oferta desde a coleta até a publicação.

---

## Filter

Componente responsável por validar critérios objetivos.

---

## Service

Camada onde toda regra de negócio deve ser implementada.

---

## Repository

Camada responsável pela persistência das informações.

---

## Bot

Camada responsável pela comunicação com plataformas externas.

---

# Regra de Ouro

Sempre que surgir dúvida sobre onde implementar uma funcionalidade, responda à seguinte pergunta:

> **"Qual é a única responsabilidade desta funcionalidade?"**

Se a resposta envolver mais de uma responsabilidade, a implementação provavelmente deve ser dividida entre diferentes camadas.

Essa regra é o principal mecanismo para manter o Projeto Renda Automática organizado, simples de evoluir e fácil de manter ao longo do tempo.
