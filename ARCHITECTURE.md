# Arquitetura do Projeto

> Este documento descreve a arquitetura de alto nível do Projeto Renda Automática.

Enquanto a documentação em `docs/` explica cada parte individualmente, este documento mostra como todas elas se conectam.

---

# Fluxo Geral

```
Marketplace

        │

        ▼

Scraper

        │

        ▼

Oferta

        │

        ▼

Pipeline

        │

        ├── Validação

        ├── Curadoria

        ├── Histórico

        ├── Classificação

        ├── Pontuação

        ├── Monetização

        ├── Formatação

        └── Publicação

        │

        ▼

Telegram
```

---

# Camadas

```
┌──────────────────────┐
│      Scrapers        │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│       Models         │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│      Services        │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│    Repositories      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│     Affiliates       │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│     Formatters       │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│      Telegram        │
└──────────────────────┘
```

---

# Responsabilidades

## Scrapers

Responsáveis por obter dados.

Jamais devem conter regras de negócio.

---

## Models

Representam entidades do domínio.

A principal entidade do projeto é:

```
Oferta
```

---

## Services

Contêm toda a lógica de negócio.

Exemplos:

- validação;
- classificação;
- curadoria;
- pontuação;
- pipeline.

---

## Repositories

Persistem informações.

Não devem decidir nada.

---

## Affiliates

Transformam links comuns em links monetizados.

Cada programa de afiliados possui sua implementação.

---

## Formatters

Transformam objetos do domínio em mensagens.

---

## Telegram

Última etapa do pipeline.

Responsável apenas pela entrega.

---

# Objetivos Arquiteturais

O projeto foi desenvolvido para possuir:

- alta coesão;
- baixo acoplamento;
- responsabilidade única;
- modularidade;
- extensibilidade;
- facilidade de testes.

---

# Regras

Toda nova funcionalidade deve responder:

- Em qual camada ela pertence?
- Existe reutilização?
- Ela aumenta o acoplamento?
- Precisa alterar o pipeline?

Se a resposta não estiver clara, a implementação deve ser reavaliada.

---

# Evolução

Novos marketplaces devem exigir apenas:

- novo scraper;
- novo afiliador;
- registro da integração.

O restante do sistema deve permanecer inalterado.

---

# Filosofia

O Projeto Renda Automática foi concebido para crescer continuamente.

A arquitetura deve permitir a adição de novas funcionalidades sem exigir reescritas frequentes.

Toda alteração deve preservar a simplicidade da estrutura existente.
