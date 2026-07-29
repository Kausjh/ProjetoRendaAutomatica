# Decisões de Arquitetura

> Este documento registra as principais decisões arquiteturais do Projeto Renda Automática e o motivo pelo qual elas foram tomadas.
>
> O objetivo não é explicar **como** o sistema funciona, mas **por que** ele foi construído dessa forma.

---

# Objetivo

Uma arquitetura não é composta apenas por código.

Ela também é composta pelas decisões que moldaram esse código.

Quando essas decisões não são documentadas, futuras alterações tendem a destruir boas abstrações simplesmente porque ninguém mais lembra por que elas existiam.

Este documento existe para evitar esse problema.

---

# 1. O pipeline é o centro da aplicação

## Decisão

Toda oferta percorre um pipeline único.

## Motivo

Em vez de vários scripts independentes executando lógica duplicada, todas as transformações acontecem em sequência sobre a mesma entidade.

Isso permite:

- previsibilidade;
- manutenção simples;
- inclusão de novas etapas;
- rastreamento do ciclo de vida da oferta.

---

# 2. A Oferta é a entidade central

## Decisão

Toda a aplicação trabalha sobre uma única entidade de domínio.

```
Oferta
```

## Motivo

Evita criar dezenas de estruturas intermediárias.

Cada etapa apenas enriquece a mesma entidade.

Vantagens:

- menos conversões;
- menos duplicação;
- menor risco de inconsistência;
- código mais simples.

---

# 3. Scrapers não possuem regras de negócio

## Decisão

Scrapers apenas coletam dados.

## Motivo

Um scraper deve continuar funcionando mesmo que toda a lógica comercial seja alterada.

Isso desacopla a coleta das decisões do sistema.

---

# 4. Regras de negócio ficam em services

## Decisão

Toda regra de negócio pertence à camada:

```
services/
```

## Motivo

Centralizar a inteligência da aplicação.

Dessa forma:

- scrapers continuam simples;
- repositories continuam responsáveis apenas por persistência;
- formatters continuam responsáveis apenas pela apresentação.

---

# 5. Persistência isolada

## Decisão

Nenhuma regra de negócio deve existir em:

```
repositories/
```

## Motivo

Repositories apenas armazenam e recuperam informações.

Misturar regras de negócio com persistência dificulta testes e manutenção.

---

# 6. Monetização isolada

## Decisão

Todo código relacionado a programas de afiliados permanece dentro de:

```
affiliates/
```

## Motivo

O restante da aplicação não precisa conhecer detalhes dos marketplaces.

Isso permite adicionar novas integrações sem alterar o pipeline.

---

# 7. Arquitetura baseada em contratos

## Decisão

Os afiliadores compartilham uma interface comum.

## Motivo

O Gerador de Links trabalha apenas com comportamentos.

Ele não precisa conhecer implementações específicas.

Isso reduz o acoplamento.

---

# 8. Configuração fora do código

## Decisão

Sempre que possível, configurações ficam em:

```
config/
```

ou

```
.env
```

## Motivo

Separar comportamento da implementação.

Alterações simples não exigem modificar código-fonte.

---

# 9. Dados de execução separados da configuração

## Decisão

Arquivos produzidos pelo sistema pertencem a:

```
database/
```

Configurações pertencem a:

```
config/
```

## Motivo

Evitar misturar dados permanentes com parâmetros da aplicação.

---

# 10. Uma responsabilidade por módulo

## Decisão

Cada módulo deve possuir uma única responsabilidade.

## Exemplos

Scraper:

- coleta.

Formatter:

- apresentação.

Repository:

- persistência.

Afiliador:

- monetização.

Service:

- regras de negócio.

---

# 11. Extensibilidade acima de rapidez

## Decisão

Novas integrações devem exigir o menor número possível de alterações.

## Motivo

O projeto foi concebido para crescer continuamente.

Adicionar um marketplace novo deve significar:

- implementar um novo scraper;
- implementar um novo afiliador;
- registrar ambos.

Sem alterar o restante da arquitetura.

---

# 12. O pipeline transforma a Oferta

A Oferta não é descartada.

Ela evolui.

```
Oferta

↓

Oferta Validada

↓

Oferta Classificada

↓

Oferta Curada

↓

Oferta Monetizada

↓

Oferta Publicada
```

Essa evolução progressiva é um dos pilares do projeto.

---

# Dívidas Técnicas Identificadas

Durante a auditoria inicial foram identificadas oportunidades de evolução.

## ExecutorPipeline

Atualmente concentra diversas responsabilidades.

No futuro poderá atuar apenas como orquestrador de etapas.

---

## Pipeline Genérico

Já existe uma infraestrutura de pipeline modular.

Parte dela ainda não é utilizada pelo fluxo principal.

Essa arquitetura poderá substituir gradualmente a implementação atual.

---

## Link de Publicação

A decisão entre:

- link original;
- link afiliado;

poderá futuramente ficar encapsulada na própria entidade `Oferta`, reduzindo acoplamento entre camadas.

---

# O que NÃO queremos

Evitar arquiteturas baseadas em:

- grandes funções;
- lógica duplicada;
- dependências circulares;
- módulos gigantes;
- decisões espalhadas;
- regras de negócio escondidas em utilitários.

---

# Filosofia do Projeto

O Projeto Renda Automática não é apenas um scraper.

Ele é uma plataforma para descoberta, análise, monetização e distribuição automatizada de oportunidades comerciais.

Toda decisão arquitetural deve preservar essa visão.

Sempre que surgir uma nova funcionalidade, a primeira pergunta deve ser:

> **"Em qual camada essa responsabilidade realmente pertence?"**

Responder corretamente essa pergunta é mais importante do que escrever o código em si.

---

# Resumo

Os pilares da arquitetura são:

- separação de responsabilidades;
- baixo acoplamento;
- alta coesão;
- pipeline centralizado;
- entidade única de domínio;
- monetização desacoplada;
- persistência isolada;
- configuração externa;
- arquitetura extensível.

Esses princípios orientam toda evolução futura do Projeto Renda Automática.
