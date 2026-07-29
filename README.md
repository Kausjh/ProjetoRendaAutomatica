# Projeto Renda Automática

> Plataforma modular para descoberta, análise, monetização e publicação automática de oportunidades comerciais utilizando programas de afiliados.

---

## Visão Geral

O Projeto Renda Automática foi desenvolvido com um objetivo simples:

> Encontrar boas ofertas automaticamente, transformá-las em links afiliados e publicá-las sem intervenção manual.

O sistema foi projetado desde o início para crescer de forma modular.

Novos marketplaces, programas de afiliados e canais de publicação podem ser adicionados sem reestruturar o restante da aplicação.

---

# Como o sistema funciona

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

        ├── Afiliação

        └── Formatação

        │

        ▼

Telegram
```

Todo o projeto gira em torno da entidade **Oferta**.

O pipeline apenas a enriquece até que esteja pronta para publicação.

---

# Arquitetura

A aplicação foi organizada em camadas.

```
┌──────────────────────────────┐
│          Scrapers            │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│          Services            │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│       Repositories           │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│         Affiliates           │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│         Telegram             │
└──────────────────────────────┘
```

A separação entre as camadas permite que cada módulo possua apenas uma responsabilidade.

---

# Estrutura do Projeto

```
ProjetoRendaAutomatica/

├── affiliates/
├── config/
├── database/
├── docs/
├── filters/
├── formatters/
├── models/
├── repositories/
├── scrapers/
├── services/

├── launcher.py
├── main.py
├── README.md
└── requirements.txt
```

---

# Tecnologias

- Python
- Playwright
- Telegram Bot API
- Mercado Livre Partner API
- Requests
- JSON
- Git
- GitHub

---

# Funcionalidades

- Coleta automática de ofertas
- Múltiplos scrapers
- Pipeline de processamento
- Curadoria comercial
- Histórico de preços
- Sistema de pontuação
- Links de afiliados
- Publicação automática no Telegram
- Arquitetura modular
- Configuração externa

---

# Pipeline

```
Marketplace

↓

Scraper

↓

Oferta

↓

Filtros

↓

Classificação

↓

Curadoria

↓

Histórico

↓

Pontuação

↓

Afiliador

↓

Formatter

↓

Telegram
```

---

# Instalação

Clone o projeto:

```bash
git clone <URL_DO_REPOSITORIO>
```

Crie um ambiente virtual:

```bash
python -m venv .venv
```

Ative:

Windows

```bash
.venv\Scripts\activate
```

Linux

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

Instale o Playwright:

```bash
playwright install
```

Crie o arquivo:

```
.env
```

Configure suas credenciais.

---

# Executando

```
python launcher.py
```

ou

```
python main.py
```

dependendo da configuração utilizada.

---

# Documentação

Toda a documentação técnica encontra-se na pasta:

```
docs/
```

Documentos disponíveis:

- Arquitetura
- Pipeline
- Modelo de Domínio
- Sistema de Afiliados
- Scrapers
- Configuração
- Instalação
- Decisões Arquiteturais
- Roadmap

---

# Princípios

O projeto foi desenvolvido seguindo os princípios:

- Responsabilidade única
- Baixo acoplamento
- Alta coesão
- Arquitetura modular
- Código extensível
- Regras de negócio centralizadas
- Persistência isolada
- Configuração externa

---

# Roadmap

Próximos objetivos:

- Amazon
- Shopee
- Kabum
- Pichau
- IA para classificação
- Dashboard Web
- Estatísticas
- Múltiplos canais de publicação
- Cobertura de testes
- Pipeline totalmente modular

Consulte:

```
docs/09-roadmap.md
```

---

# Contribuindo

Toda contribuição deve respeitar os princípios arquiteturais definidos em:

```
docs/08-decisoes-de-arquitetura.md
```

Antes de adicionar uma funcionalidade, responda:

- Em qual camada ela pertence?
- Ela aumenta o acoplamento?
- Existe reutilização possível?
- A documentação precisa ser atualizada?

---

# Licença

Este projeto é destinado a fins educacionais e de desenvolvimento pessoal.

---

# Autor

**Radar de Ofertas**

Projeto desenvolvido com foco em automação comercial, engenharia de software e arquitetura modular.

---

# Filosofia

O Projeto Renda Automática não é apenas um scraper.

Ele é uma plataforma para descoberta, análise, monetização e distribuição automatizada de oportunidades comerciais.

Toda evolução do projeto deve preservar essa ideia.

O objetivo não é apenas publicar ofertas.

O objetivo é construir uma plataforma capaz de crescer continuamente sem perder organização, simplicidade e qualidade arquitetural.
