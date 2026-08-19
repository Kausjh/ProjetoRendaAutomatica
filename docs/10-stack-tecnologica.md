# Stack Tecnológica

> Este documento descreve todas as tecnologias utilizadas no Projeto Renda Automática, suas responsabilidades, versões suportadas e critérios para adoção de novas ferramentas.

---

# Objetivo

Este documento centraliza as decisões relacionadas à stack tecnológica do projeto.

Seu objetivo é responder às seguintes perguntas:

- Quais tecnologias utilizamos?
- Por que elas foram escolhidas?
- Qual a responsabilidade de cada uma?
- Quais versões são suportadas?
- Como novas tecnologias podem ser adotadas?

---

# Filosofia

A escolha das tecnologias segue alguns princípios simples.

Sempre priorizamos:

- simplicidade;
- estabilidade;
- documentação oficial;
- comunidade ativa;
- facilidade de manutenção;
- baixo acoplamento.

Nenhuma tecnologia é utilizada apenas por popularidade.

Toda dependência deve resolver um problema real.

---

# Linguagem Principal

## Python

### Função

Linguagem principal do projeto.

Responsável por toda a lógica de negócio, scraping, automação e publicação.

### Versão mínima suportada

```text
Python 3.11
```

### Ambiente atualmente validado

```text
Python 3.13.14
```

A versão mínima é definida no `pyproject.toml`.

Novas funcionalidades devem permanecer compatíveis com Python 3.11 ou superior.

---

# Gerenciamento de Dependências

O projeto utiliza o ecossistema padrão do Python.

Ferramentas:

- pip
- pyproject.toml

Toda nova dependência deve ser registrada no arquivo oficial do projeto.

Dependências nunca devem ser instaladas manualmente sem documentação.

---

# Ambiente Virtual

Todo desenvolvimento deve ocorrer dentro de um ambiente virtual.

Estrutura esperada:

```text
.venv/
```

Nunca execute o projeto utilizando o Python global da máquina.

---

# Automação Web

## Playwright

Responsável pela automação de navegadores.

Utilizado para:

- páginas dinâmicas;
- JavaScript;
- autenticação;
- coleta de informações.

### Navegador utilizado

```text
Chromium
```

Instalação:

```bash
playwright install chromium
```

---

# Coleta HTTP

Quando possível, a coleta deve utilizar:

- requests

Playwright deve ser reservado para situações onde HTML estático não seja suficiente.

Essa estratégia reduz consumo de memória e aumenta a velocidade do pipeline.

---

# Modelagem

O domínio do projeto é representado por classes Python.

Atualmente a principal entidade é:

```text
Oferta
```

Novas entidades deverão seguir o mesmo padrão.

---

# Persistência

Atualmente:

```text
JSON
```

Arquivo principal:

```text
database/publicados.json
```

Futuras evoluções previstas:

- SQLite;
- PostgreSQL;
- Redis.

A camada de persistência deverá permanecer isolada através dos Repositories.

---

# Publicação

Atualmente:

```text
Telegram
```

A comunicação é realizada através da camada:

```text
bots/
```

Futuras integrações:

- Discord;
- WhatsApp;
- X;
- Email;
- API própria.

---

# Qualidade de Código

## Ruff

Responsável por:

- lint;
- padronização;
- boas práticas.

Execução:

```bash
ruff check .
```

Resultado esperado:

```text
O Ruff não deve reportar erros.
```

---

## MyPy

Responsável por análise estática de tipos.

Execução:

```bash
mypy .
```

### Situação atual

Existe uma limitação conhecida relacionada à duplicação do módulo:

```text
automation_web
```

Essa limitação deverá ser corrigida futuramente.

---

## Pytest

Responsável pelos testes automatizados.

Execução:

```bash
pytest
```

Resultado esperado:

```text
Todos os testes devem ser aprovados.
```

Todo novo módulo relevante deve possuir testes.

---

# Controle de Versão

Ferramenta:

```text
Git
```

Hospedagem:

```text
GitHub
```

Boas práticas:

- commits pequenos;
- mensagens claras;
- branches específicas para funcionalidades;
- Pull Requests sempre que aplicável.

---

# Estrutura do Projeto

Organização principal:

```text
bots/
config/
database/
docs/
filters/
formatters/
models/
repositories/
scrapers/
services/
tests/
```

Cada diretório representa um contexto específico do sistema.

---

# Configuração

Informações públicas:

```text
config/
```

Informações sensíveis:

```text
.env
```

Credenciais nunca devem permanecer no código-fonte.

---

# Logs

O projeto deve utilizar o módulo padrão:

```python
logging
```

Todos os componentes devem registrar eventos relevantes.

Exemplos:

- início;
- fim;
- erros;
- exceções;
- quantidade de ofertas;
- tempo de execução.

---

# Padrões Utilizados

O projeto adota os seguintes padrões:

- SRP (Single Responsibility Principle);
- baixo acoplamento;
- alta coesão;
- composição;
- arquitetura modular;
- separação entre domínio e infraestrutura.

---

# Critérios para Novas Dependências

Antes de adicionar uma nova biblioteca, as seguintes perguntas devem ser respondidas:

1. Ela resolve um problema real?
2. Existe alternativa utilizando a biblioteca padrão?
3. Possui manutenção ativa?
4. Possui documentação oficial?
5. Reduz complexidade do projeto?

Se a resposta for negativa para a maioria dessas perguntas, a dependência não deve ser adicionada.

---

# Tecnologias Previstas

## Banco de Dados

- PostgreSQL
- Redis

---

## Filas

- Celery
- RQ

---

## Cache

- Redis

---

## API

- FastAPI

---

## Painel Administrativo

- FastAPI
- HTML
- JavaScript

---

## Inteligência Artificial

Possíveis aplicações:

- classificação automática;
- categorização;
- detecção de erros de preço;
- geração de textos;
- priorização de ofertas.

---

# Processo de Atualização

Sempre que uma tecnologia for adicionada, removida ou atualizada, este documento deverá ser revisado.

As informações devem permanecer compatíveis com:

- `pyproject.toml`;
- ambiente validado;
- documentação de instalação.

---

# Ambiente Validado

| Ferramenta | Situação |
|------------|----------|
| Python 3.13.14 | ✅ |
| Ambiente Virtual | ✅ |
| Playwright Chromium | ✅ |
| pip check | ✅ |
| Ruff | ✅ |
| Pytest | ✅ |
| MyPy | ⚠️ Limitação conhecida (`automation_web`) |

---

# Resumo

A stack tecnológica do Projeto Renda Automática foi escolhida para privilegiar simplicidade, estabilidade e facilidade de evolução.

Sempre que possível, novas tecnologias deverão ser incorporadas preservando a arquitetura modular do projeto e evitando dependências desnecessárias.
