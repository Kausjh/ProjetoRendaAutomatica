<!-- 63.8738, -149.7525 -->

# Arquitetura

Este documento descreve a arquitetura atual do Projeto Renda Automática no estado da linha V10 do Social Scout.

O projeto é organizado como uma plataforma modular de descoberta, validação, análise, monetização e distribuição de ofertas de tecnologia.

A arquitetura atual possui dois caminhos principais de entrada:

1. **coleta própria**, por scrapers e integrações diretas;
2. **Social Scout**, que interpreta mensagens externas e tenta transformá-las em ofertas verificáveis.

Os dois caminhos convergem para o pipeline normal do projeto.

---

## Visão de alto nível

~~~text
                           +----------------------+
                           |     Coleta própria   |
                           | scrapers / feeds/API |
                           +----------+-----------+
                                      |
                                      v
+---------------------+      +--------+---------+
| Telegram autorizado |      | Oferta candidata |
| Social Scout listener|      +--------+---------+
+----------+----------+                |
           |                           |
           v                           |
+----------+-----------+               |
| Detector Social Scout|               |
+----------+-----------+               |
           |                           |
           v                           |
+----------+-----------+               |
| Resolver / Processador|              |
| por marketplace       |              |
+----------+-----------+               |
           |                           |
           v                           v
     +-----+-----------------------------+
     |        Oferta normalizada          |
     +----------------+-------------------+
                      |
                      v
             +--------+--------+
             | Classificação   |
             | Escopo / filtros|
             +--------+--------+
                      |
                      v
             +--------+--------+
             | Histórico       |
             | Pontuação       |
             +--------+--------+
                      |
                      v
             +--------+--------+
             | Afiliados       |
             +--------+--------+
                      |
                      v
             +--------+--------+
             | Formatação      |
             +--------+--------+
                      |
                      v
             +--------+--------+
             | Deduplicação    |
             | Persistência    |
             +--------+--------+
                      |
                      v
             +--------+--------+
             | Publicação      |
             +-----------------+
~~~

A entidade de domínio que conecta as etapas continua sendo a **Oferta**.

---

## Princípios arquiteturais

A arquitetura busca preservar:

- responsabilidade única;
- baixo acoplamento;
- alta coesão;
- componentes testáveis;
- comportamento fail-closed;
- separação entre descoberta e validação;
- separação entre identidade do produto e apresentação;
- persistência explícita de estado;
- evolução incremental por integrações específicas;
- ausência de dependência obrigatória de navegador quando uma alternativa mais simples e confiável existe.

A regra geral é evitar transformar incerteza em sucesso.

---

# Camadas principais

## Models

Representam entidades e estruturas de domínio.

Exemplos de responsabilidades:

- representar ofertas;
- transportar resultados estruturados;
- separar dados de domínio de detalhes de infraestrutura.

Os models não devem concentrar lógica de scraping, persistência ou publicação.

---

## Scrapers

Responsáveis por descobrir candidatos.

Uma fonte pode utilizar:

- HTTP;
- API;
- feed de afiliados;
- Playwright/CDP;
- dados estruturados;
- outro mecanismo específico.

O scraper deve entregar dados para o restante do pipeline sem assumir responsabilidades de todas as etapas seguintes.

O Social Scout também se integra ao projeto por meio da camada de scraping/orquestração, mas possui componentes próprios em `services/scout/`.

---

## Services

Concentram regras de negócio e integrações especializadas.

Entre as responsabilidades atuais estão:

- classificação;
- pontuação;
- geração de links afiliados;
- validação de preços;
- resolução de destinos;
- processamento específico por marketplace;
- construção de ofertas a partir do Social Scout;
- regras de escopo;
- tratamento de estados transitórios e determinísticos.

A maior parte da inteligência do Social Scout vive nesta camada.

---

## Repositories

Responsáveis por persistência e acesso a dados.

O projeto utiliza repositórios para manter responsabilidades de armazenamento fora da lógica de negócio.

Existem dados persistidos relacionados a:

- histórico de preços;
- publicações;
- estado de processamento;
- Social Scout;
- retries;
- observabilidade.

SQLite e arquivos estruturados são utilizados de acordo com a necessidade de cada componente.

---

## Filters

Aplicam regras de seleção e elegibilidade.

O objetivo é impedir que decisões de filtragem fiquem espalhadas por scrapers, formatadores ou publicadores.

---

## Formatters

Transformam dados já processados em uma representação apropriada para saída.

A formatação não deve ser responsável por descobrir produto, validar preço ou persistir estado.

---

## Bots

Representam integrações de saída, incluindo publicação em Telegram.

A camada de saída recebe uma oferta já preparada pelo pipeline.

---

# Social Scout

O Social Scout é uma segunda via de descoberta.

Ele não substitui os scrapers próprios.

Sua função é aproveitar sinais externos e submetê-los às mesmas exigências de identidade, escopo e validação antes de permitir que virem ofertas utilizáveis.

## Listener

O listener acompanha passivamente uma fonte Telegram autorizada.

Responsabilidades:

- receber novas mensagens;
- extrair dados necessários;
- persistir mensagens para processamento;
- manter o handoff de forma segura.

O listener não deve tomar decisões finais de preço, nicho ou publicação.

---

## Detector

O detector interpreta a mensagem e produz uma classificação estruturada.

Exemplos:

- oferta de produto;
- cupom geral;
- mensagem ignorável;
- marketplace identificado ou ausente;
- preço-base detectado;
- links relevantes.

O detector não deve inventar marketplace apenas com base em um domínio genérico de afiliados.

---

## Resolução

Depois da detecção, o sistema tenta provar a identidade real do destino.

A resolução é específica por marketplace quando necessário.

~~~text
Mensagem
   |
   v
Detecção
   |
   v
Links relevantes
   |
   v
Resolver
   |
   +-- identidade exata --> continua
   |
   +-- ambiguidade ------> encerra de forma segura
   |
   +-- falha transitória -> retry
   |
   +-- destino inválido --> estado determinístico
~~~

O sistema prefere rejeitar um caso incerto a escolher arbitrariamente um produto.

---

# Processadores por marketplace

## Mercado Livre

O fluxo pode resolver links até o produto real e validar dados antes de construir a oferta.

A fonte externa não é tratada como autoridade absoluta de preço.

---

## Shopee

O processador trabalha com identidade exata do produto.

Mensagens com vários links são resolvidas conservadoramente.

Regras principais:

- mesmo produto repetido pode ser aceito;
- produtos distintos geram ambiguidade;
- falha em link relevante pode manter o caso transitório;
- não há seleção arbitrária do primeiro link.

A identificação não depende de navegador quando uma identidade oficial mais direta está disponível.

---

## AliExpress

O AliExpress possui fluxo nativo e fluxo Social Scout.

No Social Scout, o destino precisa provar uma identidade real de item.

Destinos como páginas de moedas, páginas genéricas ou URLs sem identidade de produto não são tratados como produto válido.

Na coleta própria, candidatos podem vir de feeds de afiliados e depois passar por validação em página real.

O projeto reconhece estados como:

- indisponibilidade regional;
- desafio humano;
- preço não verificável;
- erro transitório.

---

## KaBuM!

O suporte Social Scout da KaBuM! foi incorporado na V10.

O domínio `tidd.ly` não é tratado como sinônimo de KaBuM!.

A arquitetura exige:

~~~text
tidd.ly
  |
  v
redirect
  |
  v
destino KaBuM!
  |
  v
URL /produto/<id>
  |
  v
ID exato
  |
  v
PDP oficial
  |
  v
JSON-LD Product
  |
  v
preço BRL
~~~

Somente depois dessa prova o marketplace pode ser enriquecido para `kabum`.

### Validação KaBuM!

A validação usa o PDP oficial e dados estruturados JSON-LD.

São avaliados:

- ID do produto;
- URL final;
- entidade `Product`;
- nome;
- preço em BRL;
- disponibilidade quando explicitamente informada.

Ausência de disponibilidade explícita permanece desconhecida.

### Cooldown de desafio humano

Desafio humano é tratado como condição operacional externa.

O sistema:

- não tenta burlar captcha;
- ativa cooldown;
- persiste o cooldown;
- impede novas tentativas durante a janela ativa.

O cooldown sobrevive a nova instância do serviço.

---

# Shadow Mode

O Social Scout opera atualmente em **Shadow Mode**.

A finalidade é permitir validação com dados reais sem ampliar prematuramente a autonomia de publicação.

O modo sombra permite observar:

- detecções;
- resoluções;
- rejeições;
- estados não verificáveis;
- erros transitórios;
- candidatos válidos;
- comportamento por marketplace.

A saída do Shadow Mode deve depender de evidência operacional suficiente, não apenas de testes automatizados.

---

# Fail-closed

Fail-closed é uma regra estrutural do projeto.

Exemplos:

~~~text
Marketplace desconhecido
=> não assume.

Identidade ambígua
=> não escolhe.

Preço divergente
=> não valida.

Cupom não confirmado
=> não declara.

Produto fora da allowlist
=> não segue.

Desafio humano
=> não burla.

Erro transitório
=> não persiste como falha terminal.
~~~

Esse comportamento é intencional.

---

# Escopo e allowlist

O Social Scout possui allowlist própria de categorias de tecnologia.

Ela funciona como uma barreira adicional entre classificação semântica e publicação.

A allowlist evita que produtos semanticamente próximos, mas fora do nicho, avancem no pipeline.

Além disso, categorias críticas podem possuir guardas adicionais.

Um exemplo é `Processador`, que recebe validação específica de contexto de CPU para reduzir falsos positivos.

---

# Estados de processamento

O Social Scout diferencia falhas determinísticas de falhas transitórias.

Exemplos de estados persistidos:

- preço rejeitado;
- não resolvida;
- preço não verificável;
- estados terminais de escopo ou suporte.

Erros genuinamente transitórios podem não ser persistidos como estado final.

Isso evita transformar uma indisponibilidade momentânea em decisão permanente.

---

# Retry, cooldown e TTL

O sistema controla reprocessamento com:

- fingerprint;
- cooldown;
- janela máxima de retry;
- estado atual;
- motivo de processamento.

O objetivo é equilibrar duas necessidades:

1. não perder oportunidades por uma falha temporária;
2. não reprocessar indefinidamente o mesmo caso.

Mudanças relevantes no fingerprint podem reiniciar a avaliação.

---

# Handoff durável

O fluxo entre recebimento e processamento utiliza persistência para reduzir perda de mensagens em caso de crash.

A estratégia busca uma semântica próxima de **at-least-once**.

Isso significa que a arquitetura prefere tolerar uma possível repetição controlada, que pode ser deduplicada, a perder silenciosamente uma oportunidade.

---

# Observabilidade

A observabilidade é separada da lógica de decisão.

Ela consulta dados persistidos e produz agregados sem exigir exposição de payloads privados.

Exemplos de métricas:

- mensagens analisadas;
- mensagens ignoradas;
- resoluções;
- preços rejeitados;
- estados não verificáveis;
- candidatos em sombra;
- erros transitórios.

A observabilidade deve permanecer read-only sobre os dados operacionais que analisa.

---

# Operação local

O ambiente atual de desenvolvimento utiliza Windows.

A inicialização é orquestrada por uma tarefa agendada que executa um supervisor versionado.

~~~text
Windows Scheduled Task
        |
        v
Supervisor PowerShell
        |
        +-- Chrome/CDP
        |
        +-- Social Scout listener
        |
        +-- Runtime principal
~~~

O supervisor verifica componentes e pode recuperar processos que deixam de executar.

A recuperação deve ser específica: um componente com problema não deve provocar reinicialização desnecessária de toda a pilha.

---

# Chrome, Playwright e CDP

Algumas integrações exigem página real.

Nesses casos o projeto pode utilizar um Chrome dedicado conectado pelo Chrome DevTools Protocol.

O navegador é tratado como infraestrutura especializada, não como requisito global.

Quando API, feed ou HTTP são suficientes, esses caminhos são preferidos.

---

# Afiliados

A camada de afiliados é separada da descoberta.

Ela recebe um link já identificado e tenta produzir um link de publicação monetizável.

O resultado mantém informações como:

- link original;
- link de publicação;
- afiliador utilizado;
- se houve transformação.

Falha de transformação não é tratada como sucesso.

---

# Pipeline normal

Depois que uma oferta candidata é construída, ela entra no pipeline normal.

~~~text
Oferta
  |
  v
Classificação
  |
  v
Filtros / escopo
  |
  v
Histórico
  |
  v
Pontuação
  |
  v
Afiliados
  |
  v
Formatação
  |
  v
Deduplicação
  |
  v
Persistência
  |
  v
Publicação
~~~

O Social Scout não deve criar um segundo pipeline incompatível com o restante do projeto.

Ele deve convergir para as mesmas estruturas de domínio.

---

# Estrutura do repositório

~~~text
ProjetoRendaAutomatica/
|
+-- bots/
+-- config/
+-- filters/
+-- formatters/
+-- models/
+-- repositories/
+-- scrapers/
+-- services/
|   +-- scout/
+-- tests/
+-- docs/
+-- scripts/
|
+-- main.py
+-- runtime.py
+-- README.md
+-- ARCHITECTURE.md
+-- STACK.md
+-- CHANGELOG.md
+-- pyproject.toml
+-- .env.example
~~~

A raiz contém também componentes legados ou utilitários que devem ser auditados antes de qualquer remoção.

Nada deve ser apagado apenas por parecer antigo.

---

# Testes

A arquitetura é protegida por uma suíte automatizada extensa.

Na linha atual existem mais de 500 testes.

Eles cobrem:

- regras de negócio;
- processadores Social Scout;
- wiring;
- persistência;
- escopo;
- retries;
- validação de marketplace;
- regressões.

Ferramentas de qualidade incluem:

- Pytest;
- Black;
- Ruff;
- pre-commit.

---

# Direção futura

A próxima evolução estrutural de maior impacto é a criação de um **Canonical Catalog**.

Hoje cada marketplace possui sua própria identidade de anúncio.

A arquitetura futura deve permitir representar:

~~~text
Produto canônico
   |
   +-- Mercado Livre
   +-- Shopee
   +-- KaBuM!
   +-- AliExpress
   +-- Amazon
~~~

A partir dessa camada será possível construir com mais consistência:

- comparação entre marketplaces;
- histórico consolidado;
- Price Intelligence;
- Alert Engine;
- API;
- app;
- web;
- extensão;
- personalização por usuário.

A identidade principal deixa de ser o anúncio.

Passa a ser o produto.
