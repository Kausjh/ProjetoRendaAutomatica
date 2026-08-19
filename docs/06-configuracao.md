# Configuração

> Este documento descreve como o Projeto Renda Automática organiza suas configurações, variáveis de ambiente e parâmetros de execução.

---

# Objetivo

O objetivo deste documento é definir um padrão único para todas as configurações do projeto.

Nenhuma configuração operacional deve ficar espalhada pelo código-fonte.

Toda configuração deve possuir um único local de definição.

---

# Princípios

O sistema segue os seguintes princípios:

- configuração centralizada;
- separação entre código e configuração;
- facilidade de manutenção;
- segurança para informações sensíveis;
- facilidade para alterar ambientes.

---

# Estrutura

```text
config/
│
├── configuracoes.py
├── logging.py
├── ambiente.py
└── ...
```

Além disso:

```text
.env
```

contém informações sensíveis.

---

# Tipos de Configuração

As configurações podem ser divididas em quatro grupos.

## Configurações da Aplicação

Controlam o comportamento geral do sistema.

Exemplos:

- quantidade máxima de ofertas;
- intervalo entre execuções;
- quantidade de páginas;
- modo debug;
- timeout.

---

## Configurações dos Scrapers

Definem parâmetros específicos da coleta.

Exemplos:

- User-Agent;
- quantidade máxima de páginas;
- tempo de espera;
- proxies;
- limite de requisições.

Cada scraper deve utilizar apenas as configurações que lhe dizem respeito.

---

## Configurações dos Bots

Controlam os canais de publicação.

Exemplos:

- Token do Telegram;
- Chat ID;
- limite de mensagens;
- intervalo entre publicações.

---

## Configurações dos Afiliadores

Definem credenciais e parâmetros utilizados pelos programas de afiliados.

Exemplos:

- IDs de afiliado;
- parâmetros UTM;
- identificadores de campanha.

---

# Variáveis de Ambiente

Informações sensíveis nunca devem ser armazenadas diretamente no código.

Esses dados devem permanecer exclusivamente no arquivo:

```text
.env
```

Exemplos:

```text
TELEGRAM_TOKEN=

TELEGRAM_CHAT_ID=

MERCADO_LIVRE_COOKIE=

SHOPEE_TOKEN=
```

O arquivo `.env` nunca deve ser enviado ao repositório.

---

# Arquivo .env.example

Todo projeto deve possuir um exemplo das variáveis esperadas.

Exemplo:

```text
TELEGRAM_TOKEN=

TELEGRAM_CHAT_ID=

DEBUG=False
```

Esse arquivo serve apenas como referência.

---

# Responsabilidades

## configuracoes.py

Responsável por concentrar todas as configurações públicas do sistema.

Exemplos:

- limites;
- constantes;
- intervalos;
- parâmetros globais.

---

## ambiente.py

Responsável por carregar variáveis provenientes do arquivo `.env`.

Nenhuma outra parte do sistema deve acessar o `.env` diretamente.

---

## logging.py

Responsável pelas configurações de logging.

Exemplos:

- nível de log;
- formato;
- destino;
- rotação.

---

# Ordem de Carregamento

Durante a inicialização do sistema, as configurações devem ser carregadas na seguinte ordem:

```text
.env

↓

ambiente.py

↓

configuracoes.py

↓

Componentes do Sistema
```

Isso garante que todos os módulos utilizem exatamente os mesmos valores.

---

# Valores Padrão

Sempre que possível, o sistema deve possuir valores padrão seguros.

Exemplo:

```python
DEBUG = False
```

Isso reduz a necessidade de configuração manual.

---

# Validação

Configurações obrigatórias devem ser validadas durante a inicialização.

Exemplos:

- token inexistente;
- Chat ID vazio;
- diretório inválido;
- variável ausente.

Caso alguma configuração obrigatória esteja ausente, o sistema deve interromper a inicialização com uma mensagem clara.

---

# Constantes

Valores constantes devem permanecer em um único local.

Exemplos:

```text
MAX_OFFERS

REQUEST_TIMEOUT

MAX_RETRIES

MIN_DISCOUNT

MAX_PRICE
```

Evite repetir números "mágicos" ao longo do projeto.

---

# Organização

As configurações devem ser agrupadas por contexto.

Exemplo:

```text
Scrapers

Bots

Afiliados

Banco

Pipeline

Logs
```

Essa organização facilita futuras expansões.

---

# Segurança

Nunca armazenar no código:

- tokens;
- senhas;
- cookies;
- chaves de API;
- credenciais.

Essas informações pertencem exclusivamente ao ambiente de execução.

---

# Ambientes

O projeto deve suportar diferentes ambientes.

Exemplo:

```text
Desenvolvimento

Homologação

Produção
```

Cada ambiente poderá possuir configurações próprias sem alterar o código.

---

# Boas Práticas

Sempre:

- utilizar variáveis de ambiente para informações sensíveis;
- documentar todas as configurações;
- fornecer valores padrão quando possível;
- validar configurações obrigatórias;
- evitar duplicação de parâmetros.

Nunca:

- acessar o `.env` diretamente fora da camada de configuração;
- espalhar constantes pelo código;
- armazenar segredos no repositório.

---

# Evolução Prevista

A arquitetura de configuração permite adicionar futuramente:

- múltiplos ambientes;
- configuração por arquivo YAML;
- configuração por JSON;
- configuração remota;
- painel administrativo;
- atualização dinâmica;
- feature flags.

Essas evoluções poderão ocorrer sem alterar a organização geral do projeto.

---

# Resumo

Toda configuração do Projeto Renda Automática deve possuir um único ponto de definição.

O código deve depender das configurações, mas nunca conhecê-las diretamente.

Essa abordagem reduz acoplamento, aumenta a segurança e facilita a manutenção da aplicação.
