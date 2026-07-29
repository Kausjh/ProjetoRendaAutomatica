# Pipeline de Execução

> Este documento descreve o fluxo operacional do Projeto Renda Automática, desde a coleta de uma oferta até sua publicação no Telegram.

---

# Visão Geral

O pipeline é o coração da aplicação.

Seu objetivo é transformar uma oferta bruta obtida em um marketplace em uma publicação monetizada e pronta para distribuição.

Cada etapa possui apenas uma responsabilidade.

Isso torna o sistema previsível, extensível e fácil de manter.

---

# Fluxo Geral

```text
Marketplace
    │
    ▼
Scraper
    │
    ▼
Oferta
    │
    ▼
Coleta Consolidada
    │
    ▼
Filtros
    │
    ▼
Classificação
    │
    ▼
Curadoria
    │
    ▼
Histórico de Preços
    │
    ▼
Pontuação
    │
    ▼
Afiliação
    │
    ▼
Formatação
    │
    ▼
Telegram
```

---

# Etapa 1 — Coleta

Responsável:

```
scrapers/
```

Objetivo:

Obter produtos dos marketplaces.

Saída:

Uma coleção de objetos `Oferta`.

Nesta etapa ainda não existe nenhuma decisão comercial.

---

# Etapa 2 — Consolidação

Responsável:

```
services/
```

Objetivo:

Reunir todas as ofertas produzidas pelos scrapers.

Nesta etapa o sistema passa a trabalhar com uma lista única de ofertas.

---

# Etapa 3 — Filtragem

Responsáveis:

```
filters/
services/
```

Objetivo:

Eliminar ofertas que não atendem aos critérios do projeto.

Exemplos:

- categoria proibida;
- preço inválido;
- produto incompleto;
- informação insuficiente.

Somente ofertas válidas continuam.

---

# Etapa 4 — Classificação

Responsável:

```
services/
```

Objetivo:

Identificar a categoria comercial da oferta.

Exemplos:

- Hardware
- SSD
- Notebook
- Monitor
- Processador

A classificação auxilia nas próximas decisões do pipeline.

---

# Etapa 5 — Curadoria

Responsável:

```
services/
```

Objetivo:

Avaliar se a oferta realmente merece ser publicada.

Nesta etapa entram regras como:

- qualidade;
- relevância;
- interesse comercial;
- aderência ao nicho.

---

# Etapa 6 — Histórico

Responsável:

```
repositories/
database/
services/
```

Objetivo:

Consultar informações históricas.

Exemplos:

- preço anterior;
- menor preço conhecido;
- variações.

Esses dados enriquecem a oferta.

---

# Etapa 7 — Pontuação

Responsável:

```
services/
```

Objetivo:

Calcular uma nota para a oferta.

Essa nota representa o potencial da publicação.

Quanto maior a pontuação, maior a qualidade da oportunidade.

---

# Etapa 8 — Afiliação

Responsável:

```
affiliates/
```

Objetivo:

Transformar um link comum em um link monetizado.

Fluxo:

```text
Oferta

↓

Gerador de Links

↓

Registro de Afiliadores

↓

Afiliador Compatível

↓

Link Afiliado
```

Caso não exista afiliador compatível, o sistema utiliza o link original.

---

# Etapa 9 — Formatação

Responsável:

```
formatters/
```

Objetivo:

Converter a oferta em uma mensagem pronta para publicação.

Exemplo:

- título;
- preço;
- desconto;
- loja;
- link;
- emojis.

Nenhuma regra de negócio deve existir aqui.

---

# Etapa 10 — Publicação

Responsável:

```
TelegramBot
```

Objetivo:

Enviar a mensagem formatada ao canal configurado.

Após a publicação, o sistema registra a operação para evitar duplicações futuras.

---

# Fluxo da Entidade Oferta

Durante toda a execução o pipeline trabalha sobre o mesmo objeto.

```text
Oferta

↓

Dados extraídos

↓

Dados validados

↓

Categoria definida

↓

Histórico anexado

↓

Pontuação calculada

↓

Link afiliado

↓

Mensagem formatada

↓

Publicação
```

A oferta é enriquecida progressivamente.

Não são criadas estruturas intermediárias para cada etapa.

---

# Responsabilidades

| Etapa | Responsabilidade |
|--------|------------------|
| Scrapers | Coletar informações |
| Services | Aplicar regras de negócio |
| Filters | Remover ofertas inválidas |
| Repositories | Persistir dados |
| Affiliates | Monetizar links |
| Formatters | Gerar mensagem |
| Telegram | Publicar |

---

# Princípios do Pipeline

Cada etapa deve:

- possuir uma única responsabilidade;
- receber dados consistentes;
- produzir uma saída previsível;
- evitar efeitos colaterais;
- depender do mínimo possível das demais etapas.

---

# Evolução Futura

A estrutura atual permite adicionar novas etapas sem alterar significativamente as existentes.

Exemplos:

- IA para classificação;
- análise de estoque;
- comparação entre marketplaces;
- detecção de erro de preço;
- previsão de viralização;
- múltiplos canais de publicação (Discord, WhatsApp, X, etc.).

O pipeline foi concebido para crescer de forma modular, preservando a separação entre coleta, processamento, monetização e distribuição.
