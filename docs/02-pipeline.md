# Pipeline de Execução

> Este documento descreve o fluxo completo de processamento de uma oferta dentro do Projeto Renda Automática, desde sua coleta até a publicação.

---

# Objetivo

O pipeline define a sequência oficial de etapas executadas pelo sistema.

Seu principal objetivo é garantir que toda oferta percorra exatamente o mesmo fluxo de processamento, tornando o comportamento da aplicação previsível, reutilizável e fácil de manter.

Cada etapa possui uma única responsabilidade.

---

# Visão Geral

Uma oferta nasce como um conjunto de dados brutos obtidos por um scraper.

Ao longo do pipeline ela é enriquecida, validada, classificada, pontuada e preparada para publicação.

Nenhuma etapa deve modificar responsabilidades pertencentes às demais.

---

# Fluxo Completo

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
Normalização
      │
      ▼
Coleta Consolidada
      │
      ▼
Validação Inicial
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
Histórico
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
Publicação
      │
      ▼
Registro
```

---

# Etapa 1 — Coleta

**Responsável**

```
scrapers/
```

## Objetivo

Obter informações diretamente das fontes configuradas.

Os scrapers apenas coletam dados.

Nenhuma regra comercial deve existir nesta etapa.

## Entrada

Nenhuma.

## Saída

Lista de objetos `Oferta`.

---

# Etapa 2 — Normalização

**Responsável**

```
models/
services/
```

## Objetivo

Garantir que todas as ofertas possuam a mesma estrutura, independentemente da origem.

Exemplos:

- converter preços;
- remover espaços;
- padronizar URLs;
- corrigir caracteres;
- tratar valores ausentes.

Ao final desta etapa todas as ofertas possuem o mesmo formato interno.

---

# Etapa 3 — Consolidação

**Responsável**

```
services/
```

## Objetivo

Reunir todas as ofertas produzidas pelos diferentes scrapers em uma única coleção.

Exemplo:

```text
Mercado Livre
          \
Amazon -----► Lista única de ofertas
          /
Kabum
```

A partir deste ponto o pipeline deixa de tratar scrapers individualmente.

---

# Etapa 4 — Validação Inicial

**Responsável**

```
services/
```

## Objetivo

Eliminar ofertas que não possuem informações mínimas para continuar.

Exemplos:

- título vazio;
- preço inválido;
- link inexistente;
- produto sem identificação.

Ofertas inválidas são descartadas imediatamente.

---

# Etapa 5 — Filtros

**Responsáveis**

```
filters/
services/
```

## Objetivo

Aplicar regras objetivas do projeto.

Exemplos:

- preço máximo;
- desconto mínimo;
- categorias proibidas;
- palavras bloqueadas;
- lojas desabilitadas.

Cada filtro executa apenas uma validação.

---

# Etapa 6 — Classificação

**Responsável**

```
services/
```

## Objetivo

Identificar o tipo da oferta.

Exemplos:

- Notebook;
- SSD;
- Processador;
- Monitor;
- Memória RAM;
- Placa de Vídeo.

Essa classificação será utilizada pelas próximas etapas.

---

# Etapa 7 — Curadoria

**Responsável**

```
services/
```

## Objetivo

Avaliar a qualidade geral da oportunidade.

Nesta etapa entram critérios subjetivos definidos pelo projeto.

Exemplos:

- relevância;
- interesse para o público;
- compatibilidade com o nicho;
- potencial de conversão.

Nem toda oferta válida merece publicação.

---

# Etapa 8 — Histórico

**Responsáveis**

```
repositories/
database/
services/
```

## Objetivo

Consultar informações históricas da oferta.

Exemplos:

- menor preço registrado;
- último preço encontrado;
- frequência da promoção;
- data da última publicação.

Esses dados enriquecem a decisão final.

---

# Etapa 9 — Pontuação

**Responsável**

```
services/
```

## Objetivo

Calcular uma nota representando a qualidade da oferta.

A pontuação poderá considerar fatores como:

- desconto;
- preço histórico;
- popularidade;
- categoria;
- confiabilidade da loja;
- estoque.

Quanto maior a pontuação, maior a prioridade de publicação.

---

# Etapa 10 — Afiliação

**Responsável**

```
affiliates/
```

## Objetivo

Transformar um link comum em um link monetizado.

Fluxo:

```text
Oferta
    │
    ▼
Gerador de Links
    │
    ▼
Registro de Afiliadores
    │
    ▼
Afiliador Compatível
    │
    ▼
Link Afiliado
```

Caso nenhum afiliador seja compatível, o link original será mantido.

---

# Etapa 11 — Formatação

**Responsável**

```
formatters/
```

## Objetivo

Gerar a mensagem que será publicada.

A mensagem pode conter:

- título;
- preço;
- desconto;
- loja;
- emojis;
- link afiliado;
- informações adicionais.

Nenhuma regra de negócio deve existir nesta camada.

---

# Etapa 12 — Publicação

**Responsável**

```
bots/
```

## Objetivo

Enviar a mensagem ao canal configurado.

Atualmente:

- Telegram.

No futuro:

- Discord;
- WhatsApp;
- X;
- E-mail.

Bots apenas publicam.

Eles nunca decidem o conteúdo.

---

# Etapa 13 — Registro

**Responsável**

```
repositories/
```

## Objetivo

Registrar que a oferta foi publicada.

Esse registro permite:

- impedir duplicações;
- consultar histórico;
- gerar estatísticas;
- auditar publicações.

A persistência ocorre somente após a publicação bem-sucedida.

---

# Ciclo de Vida da Oferta

Durante toda a execução o sistema trabalha sobre o mesmo objeto.

```text
Oferta Bruta
      │
      ▼
Oferta Normalizada
      │
      ▼
Oferta Validada
      │
      ▼
Oferta Classificada
      │
      ▼
Oferta Enriquecida
      │
      ▼
Oferta Pontuada
      │
      ▼
Oferta Monetizada
      │
      ▼
Mensagem
      │
      ▼
Publicação
```

A oferta é enriquecida progressivamente.

Não são criadas estruturas intermediárias desnecessárias.

---

# Responsabilidades do Pipeline

| Etapa | Responsabilidade |
|--------|------------------|
| Scrapers | Coletar informações |
| Models | Representar dados |
| Services | Aplicar regras de negócio |
| Filters | Validar critérios |
| Repositories | Persistir informações |
| Affiliates | Monetizar links |
| Formatters | Gerar mensagens |
| Bots | Publicar conteúdo |

---

# Garantias do Pipeline

O pipeline deve garantir que:

- toda oferta siga exatamente a mesma sequência;
- nenhuma etapa execute responsabilidades de outra;
- erros sejam isolados na etapa onde ocorreram;
- componentes possam ser substituídos sem alterar o restante do fluxo;
- novas etapas possam ser adicionadas sem reescrever as existentes.

---

# Evolução Prevista

O pipeline foi projetado para suportar futuras expansões, incluindo:

- múltiplos marketplaces;
- múltiplos afiliadores;
- IA para classificação;
- comparação automática de preços;
- detecção de erro de preço;
- análise de estoque;
- filas de processamento;
- execução paralela;
- múltiplos canais de publicação.

A evolução do sistema deve ocorrer por adição de módulos, preservando a estrutura descrita neste documento.
