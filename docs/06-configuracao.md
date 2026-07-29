# Configuração do Projeto

> Este documento descreve como o Projeto Renda Automática é configurado, quais arquivos controlam seu comportamento e como preparar uma nova instalação.

---

# Filosofia

Toda configuração da aplicação deve estar fora do código sempre que possível.

Isso permite alterar o comportamento do sistema sem modificar sua implementação.

As configurações estão distribuídas em três níveis:

- Variáveis de ambiente (`.env`);
- Arquivos da pasta `config/`;
- Constantes internas da aplicação.

---

# Estrutura

```
ProjetoRendaAutomatica/

├── .env
├── config/
│   ├── ...
│   └── *.json
└── ...
```

---

# Variáveis de Ambiente

Arquivo:

```
.env
```

O arquivo `.env` contém informações sensíveis da aplicação.

Exemplos:

- Tokens
- Chaves de API
- Credenciais
- URLs privadas
- Configurações locais

Esse arquivo **nunca deve ser enviado ao GitHub**.

---

# Arquivos da Pasta config

Diretório:

```
config/
```

Responsabilidade:

Armazenar configurações estáticas da aplicação.

Exemplos:

- marketplaces ativos;
- afiliadores habilitados;
- categorias permitidas;
- parâmetros do pipeline;
- regras de funcionamento.

Esses arquivos podem ser versionados normalmente.

---

# Diferença entre config e database

Uma regra importante do projeto:

## config/

Contém informações definidas pelo desenvolvedor.

Exemplos:

```
Categorias permitidas

Afiliadores ativos

Parâmetros
```

Esses arquivos mudam apenas quando alguém altera a configuração do sistema.

---

## database/

Contém informações produzidas durante a execução.

Exemplos:

```
Histórico

Cache

Links gerados

Publicações

Registros
```

Esses dados pertencem ao funcionamento da aplicação.

---

# Fluxo de Inicialização

Durante o início da aplicação ocorre aproximadamente o seguinte fluxo:

```
launcher.py

↓

main.py

↓

Leitura do .env

↓

Leitura da pasta config/

↓

Inicialização dos componentes

↓

Pipeline
```

A partir desse momento o sistema já possui todas as configurações necessárias para executar.

---

# Organização Recomendada

Cada arquivo da pasta `config/` deve possuir uma única responsabilidade.

Exemplo:

```
config/

├── afiliadores.json
├── categorias.json
├── telegram.json
├── filtros.json
└── ...
```

Evite arquivos enormes contendo configurações de assuntos diferentes.

---

# Informações Sensíveis

Nunca devem ficar em arquivos versionados:

- Tokens do Telegram;
- Cookies;
- Sessões autenticadas;
- Chaves privadas;
- Senhas;
- Credenciais de afiliados.

Essas informações pertencem exclusivamente ao `.env`.

---

# Arquivos Versionados

Podem ser enviados ao GitHub:

- configurações públicas;
- listas;
- categorias;
- parâmetros;
- regras;
- documentação.

Esses arquivos fazem parte da configuração do projeto.

---

# Arquivos Não Versionados

Devem permanecer apenas na máquina local:

```
.env

cookies

cache temporário

credenciais

tokens
```

---

# Boas Práticas

Sempre que uma nova configuração for criada, pergunte:

> Isso é uma configuração da aplicação ou um dado produzido pela execução?

Se for configuração:

```
config/
```

Se for informação gerada pelo sistema:

```
database/
```

Essa separação evita confusão e facilita manutenção.

---

# Objetivo

A camada de configuração existe para tornar o comportamento da aplicação previsível, reproduzível e independente do código.

Alterações de comportamento devem ocorrer prioritariamente através da configuração, preservando a implementação das regras de negócio.

---

# Resumo

| Local | Finalidade |
|--------|------------|
| `.env` | Informações sensíveis e específicas da instalação |
| `config/` | Configuração estática da aplicação |
| `database/` | Dados produzidos durante a execução |
| `services/` | Regras de negócio |
| `repositories/` | Persistência |

Essa separação mantém a arquitetura organizada e reduz o risco de alterações acidentais no comportamento do sistema.
