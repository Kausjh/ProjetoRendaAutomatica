<!-- 63.8738, -149.7525 -->

# Projeto Renda Automática

Plataforma modular para **descoberta, validação, análise, monetização e distribuição de ofertas de tecnologia**.

O projeto começou como uma automação de links de afiliado e evoluiu para um motor que combina coleta própria, sinais externos, validação direta nos marketplaces, persistência, retries e controles de segurança.

> A prioridade não é publicar o maior número possível de ofertas.
>
> A prioridade é publicar menos, mas com evidência suficiente de identidade, preço e relevância.

---

## Estado atual

O projeto está em desenvolvimento ativo.

### Social Scout

- pipeline habilitado;
- processador atual: **V10**;
- **Shadow Mode** habilitado;
- listener Telegram passivo e autorizado;
- processamento persistente;
- fingerprints, cooldowns e TTL de retry;
- resolução específica por marketplace;
- validação de identidade e preço;
- allowlist de nicho;
- proteções fail-closed;
- observabilidade sem depender de payloads privados.

O Shadow Mode permite executar o fluxo real sem liberar automaticamente todas as decisões do Social Scout para publicação. A saída desse modo depende de evidência operacional suficiente.

### Qualidade

Na validação final da V10, a suíte chegou a **562 testes aprovados**.

Ferramentas de qualidade:

- Pytest
- Black
- Ruff
- pre-commit
- `git diff --check`

---

## Visão geral

```text
Fontes
  |
  +-- Coleta própria
  |
  +-- Social Scout
  |
  v
Detecção
  |
  v
Identificação do produto
  |
  v
Resolução do marketplace
  |
  v
Validação de identidade
  |
  v
Validação de preço
  |
  v
Classificação e escopo
  |
  v
Histórico / pontuação
  |
  v
Afiliados
  |
  v
Deduplicação / persistência
  |
  v
Publicação
```

A entidade central continua sendo a **Oferta**. Cada camada adiciona evidências e contexto antes de permitir que ela avance.

---

## Fontes de descoberta

### Coleta própria

Scrapers e integrações específicas procuram produtos diretamente nas fontes suportadas.

Dependendo do marketplace, uma integração pode usar:

- APIs;
- feeds de afiliados;
- HTTP;
- Playwright;
- Chrome DevTools Protocol;
- páginas de produto;
- JSON-LD e outros dados estruturados.

O projeto não força todos os marketplaces a usar a mesma estratégia.

### Social Scout

O Social Scout observa passivamente mensagens recebidas por uma conta Telegram autorizada e tenta transformar sinais externos em ofertas verificáveis.

A mensagem externa é tratada como uma **pista**, não como fonte absoluta de verdade.

```text
Mensagem
   |
   v
Detector
   |
   v
Oferta de produto?
   |
   v
Marketplace conhecido?
   |
   +-- sim --> processador específico
   |
   +-- não --> resolução conservadora quando suportada
                    |
                    v
             identidade exata
                    |
                    v
             validação real
```

Sempre que possível, identidade e preço são confrontados com a fonte oficial.

---

## Marketplaces

### Mercado Livre

O projeto possui integração para descoberta e processamento de ofertas do Mercado Livre.

No Social Scout, links podem ser resolvidos até o destino real antes da validação. O preço informado por uma fonte externa não é tratado automaticamente como preço oficial.

### Shopee

A Shopee possui processamento específico no Social Scout.

A identidade do produto é priorizada sobre inferências baseadas apenas em título. Mensagens com múltiplos links são tratadas de forma conservadora:

- repetições da mesma identidade podem ser aceitas;
- produtos diferentes geram ambiguidade;
- falhas de resolução podem permanecer transitórias;
- nenhum link é escolhido arbitrariamente só por aparecer primeiro.

A identificação não depende de navegador quando uma forma mais precisa e simples já é suficiente.

### AliExpress

O AliExpress aparece em dois fluxos.

#### Coleta própria

A coleta nativa pode usar feeds da Awin como fonte de candidatos e validar o produto depois.

O sistema reconhece condições como:

- indisponibilidade regional;
- preço não verificável;
- página inválida;
- desafio humano;
- falha transitória.

Condições conhecidas podem receber cache temporário para evitar tentativas repetitivas sem benefício.

#### Social Scout

Links curtos não são assumidos como produtos. O fluxo exige uma identidade real de item e rejeita destinos como:

- páginas de moedas;
- páginas genéricas;
- destinos sem ID de produto;
- destinos ambíguos;
- páginas indisponíveis.

### KaBuM!

O suporte à KaBuM! entrou no Social Scout na **V10**.

O domínio `tidd.ly` não é tratado como sinônimo de KaBuM!. Ele é apenas um redirecionador e o destino precisa ser provado.

```text
tidd.ly
   |
   v
redirect
   |
   v
destino final
   |
   v
host KaBuM?
   |
   v
URL de produto?
   |
   v
ID exato?
   |
   v
validação do PDP
```

A validação do PDP usa JSON-LD quando disponível para analisar:

- identidade;
- nome;
- moeda;
- preço;
- disponibilidade.

Ausência de disponibilidade explícita não significa automaticamente falta de estoque.

Quando a página apresenta desafio humano, o projeto **não tenta contorná-lo**. Um cooldown persistente reduz novas tentativas durante o período de proteção.

### Amazon

O projeto possui componentes relacionados à Amazon e monetização por afiliados.

O suporte Amazon dentro do Social Scout ainda não faz parte do fluxo atual.

---

## Filosofia fail-closed

O projeto prefere perder uma oportunidade a publicar uma informação errada.

```text
Marketplace não comprovado
→ não assume.

Dois produtos diferentes
→ ambiguidade.

Preço divergente
→ rejeição ou estado não verificável.

Cupom não confirmado
→ não declara como validado.

Produto fora do nicho
→ não segue.

Desafio humano
→ não tenta burlar.

Falha transitória
→ retry controlado.
```

A ausência de evidência não é tratada como evidência positiva.

---

## Escopo do Social Scout

O Social Scout possui uma allowlist própria.

Categorias atualmente aceitas:

- Armazenamento
- Computador e Mini PC
- Console
- Controle
- Fonte e energia
- Gabinete
- Iluminação de setup
- Kit upgrade
- Memória RAM
- Microfone
- Monitor
- Mouse e mousepad
- Notebook
- Placa de vídeo
- Placa-mãe
- Processador
- Realidade virtual
- Rede
- Refrigeração de PC
- Simulação
- Streaming e captura
- Suportes e conectividade
- Teclado
- Áudio

A expansão do escopo deve ser deliberada.

---

## Proteção contra falsos positivos

Classificação semântica isolada não é suficiente em todos os casos.

Durante o desenvolvimento, um produto de cozinha foi classificado semanticamente como **Processador**. A partir disso, a categoria recebeu uma verificação adicional de contexto de hardware.

A lógica procura evidências compatíveis com CPUs reais, como fabricantes, famílias, sockets e nomenclaturas técnicas.

---

## Preço, histórico e pontuação

O projeto diferencia conceitos como:

- preço informado pela fonte;
- preço oficial;
- preço original;
- preço promocional;
- preço com cupom;
- preço verificável;
- preço histórico.

Também existem componentes de histórico de preços e pontuação de ofertas.

Isso permite evoluir de uma lógica simples:

```text
"O preço está abaixo de X?"
```

para perguntas melhores:

```text
"Esse preço realmente está bom para este produto?"
```

Essa base prepara o caminho para **Price Intelligence**.

---

## Afiliados

A camada de afiliados mantém separadas informações como:

- link original;
- link de publicação;
- afiliador utilizado;
- transformação realizada ou não.

Uma falha de transformação não é registrada como sucesso.

O projeto possui fluxos relacionados a:

- Mercado Livre;
- Shopee;
- Amazon;
- Awin.

KaBuM! e AliExpress fazem parte das integrações relacionadas à Awin.

---

## Persistência, retry e deduplicação

O sistema não começa do zero a cada execução.

São persistidas informações relacionadas a:

- histórico de preços;
- publicações;
- Social Scout;
- estados de processamento;
- fingerprints;
- retries;
- deduplicação;
- observabilidade.

O Social Scout diferencia estados transitórios e terminais, aplica cooldowns e limita a janela de retry.

Mudanças relevantes no conteúdo podem produzir um novo fingerprint e permitir nova avaliação.

---

## Handoff durável

O pipeline possui mecanismos para reduzir perda de trabalho entre processamento e confirmação.

A intenção é manter uma semântica próxima de **at-least-once**, combinada com persistência e deduplicação para controlar repetições.

---

## Observabilidade

O projeto possui ferramentas de observabilidade para acompanhar agregados operacionais sem depender da exposição de mensagens privadas.

Exemplos:

- mensagens processadas;
- mensagens ignoradas;
- resoluções;
- preços rejeitados;
- estados não verificáveis;
- candidatos em Shadow Mode;
- erros transitórios.

---

## Operação automática

No ambiente Windows de desenvolvimento existe um supervisor responsável por manter componentes operacionais ativos.

```text
Supervisor
   |
   +-- Runtime principal
   |
   +-- Social Scout listener
   |
   +-- Chrome dedicado / CDP
```

Uma tarefa agendada do Windows atua como ponto de inicialização.

O supervisor pode recuperar componentes que deixam de executar.

---

## Arquitetura

```text
ProjetoRendaAutomatica/
|
+-- bots/
|   +-- integrações de saída
|
+-- config/
|   +-- configuração
|
+-- filters/
|   +-- filtragem
|
+-- formatters/
|   +-- apresentação
|
+-- models/
|   +-- domínio
|
+-- repositories/
|   +-- persistência
|
+-- scrapers/
|   +-- descoberta
|
+-- services/
|   +-- regras de negócio
|   +-- validações
|   +-- afiliados
|   +-- Social Scout
|
+-- tests/
|   +-- testes automatizados
|
+-- docs/
|   +-- documentação técnica
|
+-- main.py
+-- runtime.py
+-- pyproject.toml
+-- README.md
+-- .env.example
```

Princípios buscados:

- responsabilidade única;
- baixo acoplamento;
- alta coesão;
- testabilidade;
- extensibilidade;
- evolução incremental.

Para detalhes, consulte `ARCHITECTURE.md`.

---

## Tecnologias principais

- Python
- Playwright
- Telethon
- Telegram Bot API
- SQLite
- JSON
- Awin
- Pytest
- Black
- Ruff
- pre-commit
- Git
- GitHub
- PowerShell

---

## Configuração e segurança

Configurações locais e segredos não devem ficar no código.

O projeto usa `.env` para valores específicos de ambiente e mantém `.env.example` como referência pública.

O repositório público não deve conter:

- credenciais;
- tokens;
- códigos de autenticação;
- sessões Telegram;
- bancos locais de produção;
- perfis de navegador;
- payloads privados;
- identificadores privados desnecessários.

Arquivos sensíveis de runtime são protegidos por `.gitignore`.

---

## Documentação

Arquivos importantes:

- `ARCHITECTURE.md`
- `STACK.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `docs/`

A documentação deve evoluir junto com o código.

---

## Roadmap

A direção de longo prazo é transformar o motor atual em uma plataforma própria de inteligência de compras.

```text
Social Scout + Scrapers
          |
          v
   Canonical Catalog
          |
          v
   Price Intelligence
          |
          v
     Alert Engine
          |
          v
         API
          |
          v
   App / Web / Extensão
```

### Canonical Catalog

A meta é criar uma identidade própria para cada produto, independente do marketplace.

```text
AMD Ryzen 7 5700X
|
+-- Mercado Livre
+-- Shopee
+-- KaBuM!
+-- AliExpress
+-- Amazon
```

O anúncio deixa de ser a identidade principal. O produto passa a ser.

### Price Intelligence

Evoluções planejadas:

- histórico consolidado;
- comparação entre marketplaces;
- referência de preço normal;
- detecção de quedas relevantes;
- preço final;
- análise de oportunidade real.

### Alert Engine

Exemplos de regras futuras:

```text
"Avise quando uma RTX atingir determinado preço."
```

```text
"Avise quando este produto estiver abaixo da média histórica."
```

### Plataforma pública

Etapas futuras podem incluir:

- API própria;
- contas de usuários;
- preferências;
- watchlists;
- notificações push;
- feed personalizado;
- app;
- interface web;
- extensão de navegador;
- ferramentas para criadores e parceiros.

---

## Princípios do projeto

Antes de adicionar uma funcionalidade:

1. A qual camada ela pertence?
2. Ela aumenta desnecessariamente o acoplamento?
3. Existe identidade verificável para o dado?
4. Estamos assumindo algo que poderíamos validar?
5. O comportamento falha de forma segura?
6. A funcionalidade pode ser testada?
7. A documentação precisa ser atualizada?

---

## Filosofia

O Projeto Renda Automática não é apenas um scraper.

Ele está sendo construído como uma plataforma para:

**descobrir → verificar → analisar → monetizar → distribuir**

oportunidades comerciais de forma automatizada.

---

## Contribuindo

Consulte `CONTRIBUTING.md` antes de propor alterações estruturais.

---

## Licença

Distribuído sob licença MIT.

Consulte `LICENSE`.

---

## Autor

**Kauê Jhonatas**

Projeto desenvolvido com foco em automação comercial, engenharia de software, inteligência de preços e arquitetura modular.
