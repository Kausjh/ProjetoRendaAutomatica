# Modelo de Domínio

> Este documento descreve as entidades que representam o domínio do Projeto Renda Automática, suas responsabilidades e como evoluem durante o pipeline de processamento.

---

# Objetivo

O domínio representa o problema que o software resolve.

O Projeto Renda Automática não existe para apenas coletar produtos.

Seu objetivo é identificar oportunidades comerciais, enriquecê-las com informações relevantes, monetizá-las e publicá-las automaticamente.

Todo o restante da arquitetura existe para transformar dados brutos em uma publicação de alta qualidade.

---

# Princípios do Modelo de Domínio

O domínio foi projetado seguindo os seguintes princípios:

- uma única entidade principal durante todo o pipeline;
- baixo acoplamento entre entidades;
- enriquecimento progressivo dos dados;
- separação entre estado e comportamento;
- regras de negócio concentradas em Services.

---

# Entidade Central

A principal entidade do sistema é:

```text
Oferta
```

Toda a aplicação gira em torno dela.

A Oferta nasce no Scraper e percorre todas as etapas do pipeline até sua publicação.

Ela não é substituída durante a execução.

Ela é continuamente enriquecida.

---

# Ciclo de Vida da Oferta

```text
Marketplace
      │
      ▼
Produto encontrado
      │
      ▼
Oferta criada
      │
      ▼
Oferta normalizada
      │
      ▼
Oferta validada
      │
      ▼
Oferta classificada
      │
      ▼
Oferta enriquecida
      │
      ▼
Oferta monetizada
      │
      ▼
Mensagem gerada
      │
      ▼
Oferta publicada
```

Cada etapa adiciona novas informações sem perder as anteriores.

---

# Estrutura Conceitual da Oferta

A Oferta pode ser dividida logicamente em seis grupos de informações.

## 1. Dados de Origem

Representam exatamente aquilo que foi encontrado na fonte.

Exemplos:

- título;
- preço;
- preço anterior;
- URL original;
- imagem;
- loja;
- marketplace;
- categoria informada pela loja.

Esses dados devem permanecer o mais próximos possível da origem.

---

## 2. Dados Normalizados

Informações convertidas para um formato interno padronizado.

Exemplos:

- preço convertido para número;
- título limpo;
- URL padronizada;
- caracteres corrigidos;
- categorias normalizadas.

Esses dados tornam todas as ofertas compatíveis entre si.

---

## 3. Dados Comerciais

Representam informações calculadas pelo sistema.

Exemplos:

- desconto;
- economia;
- menor preço histórico;
- preço médio;
- relevância;
- prioridade.

Esses dados enriquecem a análise da oferta.

---

## 4. Dados de Classificação

Representam decisões tomadas durante o pipeline.

Exemplos:

- categoria comercial;
- nicho;
- score;
- prioridade;
- qualidade da oferta.

Esses atributos não existem na origem.

São produzidos pelo sistema.

---

## 5. Dados de Monetização

Criados após a etapa de afiliação.

Exemplos:

- link afiliado;
- afiliador utilizado;
- comissão prevista;
- plataforma de afiliação.

Esses dados permitem transformar uma oferta em receita.

---

## 6. Dados de Publicação

Representam o estado final da oferta.

Exemplos:

- mensagem formatada;
- data de publicação;
- canal utilizado;
- identificador da mensagem;
- status da publicação.

---

# Evolução da Entidade

A Oferta evolui continuamente.

```text
Oferta

↓

Dados Originais

↓

Dados Normalizados

↓

Dados Comerciais

↓

Dados Históricos

↓

Classificação

↓

Pontuação

↓

Monetização

↓

Mensagem

↓

Publicação
```

Nenhuma etapa substitui a entidade.

Cada etapa adiciona novas informações.

---

# Responsabilidades da Oferta

A entidade Oferta deve representar apenas o estado da oportunidade comercial.

Ela pode possuir comportamentos simples relacionados aos próprios dados.

Exemplos:

- calcular percentual de desconto;
- verificar se possui imagem;
- verificar se possui preço válido;
- propriedades derivadas.

---

# O que a Oferta NÃO deve fazer

A entidade nunca deve:

- acessar internet;
- executar scraping;
- acessar banco de dados;
- publicar mensagens;
- consumir APIs;
- decidir estratégia de negócio.

Sempre que isso acontecer, a responsabilidade pertence a outra camada.

---

# Objetos que Transformam a Oferta

| Componente | Responsabilidade |
|------------|------------------|
| Scraper | Criar a Oferta |
| Service | Enriquecer a Oferta |
| Filter | Validar critérios |
| Repository | Consultar histórico |
| Affiliate | Monetizar links |
| Formatter | Gerar mensagem |
| Bot | Publicar conteúdo |

Todos esses componentes modificam ou utilizam a mesma entidade.

---

# Invariantes do Domínio

Independentemente da etapa do pipeline, algumas regras sempre devem permanecer verdadeiras.

Uma Oferta deve possuir:

- identificação da origem;
- título;
- URL válida;
- preço atual.

Sem essas informações a Oferta não pode continuar no pipeline.

---

# Entidades Futuras

Embora atualmente a Oferta seja a principal entidade, o domínio foi projetado para suportar novos modelos.

Exemplos:

## Produto

Representa um item independente da oferta encontrada.

---

## Loja

Representa o marketplace ou vendedor.

---

## Categoria

Representa classificações internas do sistema.

---

## Histórico de Preços

Representa a evolução temporal dos preços de um produto.

---

## Publicação

Representa uma oferta já enviada para algum canal.

---

## Afiliador

Representa uma plataforma responsável pela monetização dos links.

---

# Relacionamento Conceitual

```text
Marketplace
      │
      ▼
Oferta
      │
      ├────────► Histórico
      │
      ├────────► Categoria
      │
      ├────────► Afiliador
      │
      └────────► Publicação
```

A Oferta permanece como centro do domínio.

As demais entidades apenas complementam suas informações.

---

# Regras de Evolução

Novos atributos devem ser adicionados à Oferta somente quando fizerem parte da própria oportunidade comercial.

Caso representem outro conceito do negócio, uma nova entidade deve ser criada.

Essa regra evita que a Oferta se transforme em um objeto excessivamente grande.

---

# Resumo

A Oferta representa o ativo mais importante do Projeto Renda Automática.

Ela nasce como um conjunto de dados coletados de um marketplace e termina como uma oportunidade comercial enriquecida, classificada, monetizada e publicada.

Toda evolução futura do sistema deve preservar esse princípio:

> **O pipeline transforma a Oferta. Ele não substitui a Oferta.**
