# Modelo de Domínio

> Este documento descreve as entidades que representam o domínio do Projeto Renda Automática e como elas evoluem ao longo da execução do sistema.

---

# O que é o domínio?

O domínio representa o problema que o software resolve.

Neste projeto, o objetivo não é apenas coletar produtos.

O objetivo é transformar oportunidades comerciais em publicações monetizadas.

Todo o restante da arquitetura existe para enriquecer essas oportunidades até que estejam prontas para publicação.

---

# A entidade central

A principal entidade do sistema é:

```
Oferta
```

Toda a aplicação gira em torno dela.

O pipeline não cria novas entidades para cada etapa.

Ele modifica e enriquece continuamente a mesma `Oferta`.

---

# Ciclo de vida da Oferta

```
Marketplace

↓

Produto encontrado

↓

Oferta criada

↓

Validação

↓

Classificação

↓

Curadoria

↓

Histórico

↓

Pontuação

↓

Afiliação

↓

Formatação

↓

Publicação
```

---

# Estrutura lógica da Oferta

Os atributos da Oferta podem ser organizados em cinco grupos.

## 1. Dados de Origem

Representam exatamente o que foi encontrado no marketplace.

Exemplos:

- título;
- preço;
- preço anterior;
- loja;
- URL original;
- imagem;
- categoria;
- identificação do marketplace.

Esses dados não devem ser modificados.

---

## 2. Dados Comerciais

São calculados durante a execução.

Exemplos:

- percentual de desconto;
- economia;
- histórico de preços;
- melhor preço;
- relevância.

Essas informações enriquecem a oferta.

---

## 3. Dados de Monetização

São adicionados após a etapa de afiliação.

Exemplos:

- link afiliado;
- marketplace compatível;
- afiliador utilizado.

Esses dados não existem quando a oferta nasce.

---

## 4. Dados de Classificação

Representam decisões tomadas pelo pipeline.

Exemplos:

- categoria comercial;
- nicho;
- score;
- prioridade.

Esses dados determinam se vale a pena publicar.

---

## 5. Dados de Publicação

Representam a etapa final.

Exemplos:

- mensagem formatada;
- data da publicação;
- status;
- identificador da publicação.

---

# Evolução da Oferta

Durante a execução a mesma entidade é enriquecida.

```
Oferta

↓

Scraper

↓

Oferta + Dados

↓

Filtros

↓

Oferta Validada

↓

Classificação

↓

Oferta Classificada

↓

Curadoria

↓

Oferta Selecionada

↓

Afiliador

↓

Oferta Monetizada

↓

Formatter

↓

Mensagem

↓

Telegram
```

---

# Responsabilidades da Entidade

A entidade Oferta deve representar apenas o estado da oportunidade comercial.

Ela pode conter regras simples relacionadas aos seus próprios dados.

Exemplos:

- cálculo de desconto;
- propriedades derivadas;
- verificações simples.

Ela **não deve**:

- acessar APIs;
- gravar banco;
- consultar Telegram;
- executar scrapers;
- decidir estratégia comercial.

---

# Objetos que transformam a Oferta

Ao longo do pipeline diversos componentes modificam a Oferta.

| Componente | Responsabilidade |
|------------|------------------|
| Scraper | Criar a Oferta |
| Filter | Validar |
| Services | Enriquecer |
| Repositories | Consultar histórico |
| Affiliates | Monetizar |
| Formatter | Preparar publicação |
| Telegram | Publicar |

---

# Princípio Fundamental

O projeto utiliza uma única entidade de domínio durante todo o pipeline.

Isso reduz duplicação de dados, facilita manutenção e evita conversões desnecessárias entre estruturas intermediárias.

Sempre que possível, novas informações devem ser adicionadas à própria Oferta, preservando seu papel como entidade central do sistema.

---

# Evoluções Futuras

A entidade Oferta poderá incorporar novas informações sem alterar a arquitetura geral.

Exemplos:

- estoque disponível;
- frete;
- vendedor;
- cashback;
- prazo de entrega;
- cupom aplicado;
- confiança da oferta;
- probabilidade de viralização.

Como todo o pipeline trabalha sobre a mesma entidade, novas capacidades podem ser adicionadas com impacto mínimo no restante do sistema.

---

# Resumo

A Oferta representa o ativo mais importante do Projeto Renda Automática.

Ela nasce como um conjunto de dados coletados dos marketplaces e termina como uma oportunidade comercial enriquecida, monetizada e publicada.

Toda evolução futura do sistema deve preservar esse princípio: **o pipeline transforma a Oferta; ele não substitui a Oferta.**
