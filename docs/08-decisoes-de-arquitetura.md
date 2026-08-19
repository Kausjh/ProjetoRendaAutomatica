# Decisões de Arquitetura

> Este documento reúne as principais decisões arquiteturais adotadas no Projeto Renda Automática e os motivos que levaram à sua escolha.

---

# Objetivo

Durante a evolução do projeto, diversas decisões técnicas precisarão ser tomadas.

Sem documentação, essas decisões acabam sendo esquecidas, fazendo com que o projeto retorne a discussões já resolvidas.

Este documento existe para registrar essas escolhas.

Sempre que uma decisão arquitetural importante for tomada, ela deverá ser adicionada aqui.

---

# Como Registrar uma Nova Decisão

Cada decisão deve seguir a estrutura:

- Identificador;
- Status;
- Data;
- Contexto;
- Decisão;
- Consequências.

Exemplo:

```text
ADR-0001

Status:
Aceita

Data:
2026-07-29

Contexto:
...

Decisão:
...

Consequências:
...
```

---

# ADR-0001

## Título

Arquitetura Modular por Responsabilidade.

## Status

Aceita.

## Data

2026-07-29

## Contexto

O projeto crescerá continuamente com novos scrapers, novos afiliadores e novos canais de publicação.

Uma arquitetura fortemente acoplada tornaria essa expansão cada vez mais difícil.

## Decisão

O sistema será dividido em módulos especializados.

Cada módulo possuirá apenas uma responsabilidade principal.

## Consequências

### Positivas

- maior organização;
- menor acoplamento;
- facilidade para testes;
- facilidade de manutenção.

### Negativas

- maior quantidade de arquivos;
- maior disciplina arquitetural.

---

# ADR-0002

## Título

Objeto Oferta como entidade central.

## Status

Aceita.

## Data

2026-07-29

## Contexto

Era necessário definir se o pipeline criaria diferentes objetos durante o processamento ou se trabalharia sempre sobre uma única entidade.

## Decisão

Todo o pipeline trabalhará sobre um único objeto:

```text
Oferta
```

Esse objeto será enriquecido progressivamente.

## Consequências

### Positivas

- menor complexidade;
- menor duplicação;
- menor quantidade de conversões.

### Negativas

A entidade poderá crescer ao longo do tempo.

Será necessário manter disciplina para evitar excesso de responsabilidades.

---

# ADR-0003

## Título

Uso de BaseScraper.

## Status

Aceita.

## Contexto

Todos os scrapers compartilham comportamentos semelhantes.

## Decisão

Todo scraper deverá herdar de:

```text
BaseScraper
```

## Consequências

### Positivas

- reutilização de código;
- padronização;
- menor duplicação.

### Negativas

Mudanças na classe base exigem atenção para evitar impactos em todos os scrapers.

---

# ADR-0004

## Título

Pipeline Linear.

## Status

Aceita.

## Contexto

Era necessário definir se o processamento ocorreria por chamadas independentes ou por uma sequência fixa.

## Decisão

Toda oferta deverá percorrer exatamente o mesmo pipeline arquitetural.

```text
Coleta

↓

Normalização

↓

Validação

↓

Filtragem

↓

Classificação

↓

Pontuação

↓

Monetização (Afiliados)

↓

Formatação

↓

Publicação

↓

Persistência
```

Nenhuma etapa poderá ser ignorada sem que isso seja uma decisão arquitetural explícita.

Novas etapas poderão ser adicionadas futuramente, desde que preservem a ordem lógica do pipeline e não aumentem o acoplamento entre os módulos.

## Consequências

### Positivas

- previsibilidade;
- facilidade para testes;
- facilidade de depuração.

### Negativas

Fluxos muito específicos poderão exigir etapas opcionais no futuro.

---

# ADR-0005

## Título

Configuração Centralizada.

## Status

Aceita.

## Contexto

Configurações espalhadas pelo código dificultam manutenção.

## Decisão

Toda configuração deverá permanecer na camada:

```text
config/
```

Credenciais permanecerão no:

```text
.env
```

## Consequências

### Positivas

- segurança;
- facilidade de manutenção;
- menor duplicação.

---

# ADR-0006

## Título

Sistema de Afiliados Independente.

## Status

Aceita.

## Contexto

Cada plataforma de afiliados possui regras próprias.

Misturar essas regras ao restante do sistema aumentaria o acoplamento.

## Decisão

Cada afiliador será implementado de forma independente.

Todos utilizarão a mesma interface.

## Consequências

### Positivas

- fácil substituição;
- fácil expansão;
- isolamento entre plataformas.

---

# ADR-0007

## Título

Separação entre Regra de Negócio e Infraestrutura.

## Status

Aceita.

## Contexto

Misturar scraping, banco e lógica comercial dificulta manutenção.

## Decisão

Toda regra de negócio ficará concentrada na camada:

```text
services/
```

As demais camadas fornecerão apenas infraestrutura.

## Consequências

### Positivas

- maior organização;
- código mais reutilizável;
- testes simplificados.

---

# ADR-0008

## Título

Persistência Abstraída.

## Status

Aceita.

## Contexto

O mecanismo de armazenamento poderá mudar futuramente.

## Decisão

Toda persistência ocorrerá através de:

```text
repositories/
```

O restante do sistema não conhecerá o mecanismo utilizado.

## Consequências

### Positivas

- troca simples de banco;
- menor acoplamento.

---

# ADR-0009

## Título

Comunicação Externa Isolada.

## Status

Aceita.

## Contexto

Telegram, Discord e futuras integrações possuem APIs diferentes.

## Decisão

Toda comunicação externa ficará concentrada na camada:

```text
bots/
```

## Consequências

### Positivas

- fácil substituição;
- múltiplos canais;
- baixo acoplamento.

---

# ADR-0010

## Título

Evolução por Extensão.

## Status

Aceita.

## Contexto

O projeto deverá crescer continuamente.

## Decisão

Sempre que possível, novas funcionalidades serão adicionadas por extensão e não por alteração de módulos existentes.

## Consequências

### Positivas

- menor risco de regressões;
- maior estabilidade;
- crescimento previsível.

---

# Decisões Futuras

As próximas decisões relevantes deverão ser registradas seguindo o mesmo padrão.

Exemplos:

- adoção de filas;
- processamento paralelo;
- cache distribuído;
- IA para classificação;
- banco de dados relacional;
- sistema de plugins;
- API pública;
- painel administrativo.

---

# Histórico

| ADR | Título | Status |
|------|--------|--------|
| ADR-0001 | Arquitetura Modular | Aceita |
| ADR-0002 | Oferta como Entidade Central | Aceita |
| ADR-0003 | BaseScraper | Aceita |
| ADR-0004 | Pipeline Linear | Aceita |
| ADR-0005 | Configuração Centralizada | Aceita |
| ADR-0006 | Sistema de Afiliados | Aceita |
| ADR-0007 | Regra de Negócio em Services | Aceita |
| ADR-0008 | Persistência Abstraída | Aceita |
| ADR-0009 | Comunicação Externa Isolada | Aceita |
| ADR-0010 | Evolução por Extensão | Aceita |

---

# Resumo

Toda decisão arquitetural importante deve ser registrada antes ou imediatamente após sua implementação.

Isso evita retrabalho, preserva o histórico técnico do projeto e facilita a entrada de novos desenvolvedores.
