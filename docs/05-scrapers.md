# Scrapers

> Este documento define a arquitetura, as responsabilidades e os padrões de implementação dos scrapers do Projeto Renda Automática.

---

# Objetivo

Os scrapers são responsáveis por coletar informações em fontes externas e convertê-las para o modelo interno utilizado pelo sistema.

Eles representam a porta de entrada de dados do pipeline.

Toda oferta existente no sistema nasce em um scraper.

---

# Objetivos Arquiteturais

A arquitetura dos scrapers foi projetada para oferecer:

- padronização;
- baixo acoplamento;
- reutilização de código;
- facilidade para adicionar novas lojas;
- facilidade de testes;
- manutenção simples;
- isolamento entre fontes.

Cada scraper deve ser completamente independente dos demais.

---

# Fluxo Geral

```text
Fonte Externa
      │
      ▼
Download dos Dados
      │
      ▼
Extração
      │
      ▼
Normalização Inicial
      │
      ▼
Objeto Oferta
      │
      ▼
Pipeline
```

O scraper termina sua responsabilidade no momento em que retorna objetos `Oferta`.

---

# Organização

```text
scrapers/
│
├── base_scraper.py
├── mercado_livre.py
├── amazon.py
├── kabum.py
├── pichau.py
├── shopee.py
└── ...
```

Cada arquivo representa apenas uma fonte de dados.

---

# BaseScraper

Todos os scrapers devem herdar de `BaseScraper`.

A interface mínima esperada é:

```python
class BaseScraper:

    def collect(self):
        ...

    def parse(self):
        ...

    def run(self):
        ...
```

A implementação interna pode variar, mas a interface pública deve permanecer consistente.

---

# Responsabilidades

Um scraper deve:

- acessar uma fonte externa;
- localizar os dados necessários;
- interpretar HTML ou JSON;
- tratar paginação;
- converter informações para objetos Oferta;
- registrar erros relacionados à coleta.

Nada além disso.

---

# Responsabilidades Proibidas

Um scraper nunca deve:

- publicar mensagens;
- acessar Telegram;
- salvar histórico;
- consultar banco de dados;
- aplicar filtros;
- calcular pontuação;
- gerar links de afiliados;
- formatar mensagens;
- decidir se uma oferta será publicada.

Toda lógica de negócio pertence ao pipeline.

---

# Entrada

A entrada de um scraper pode incluir:

- URL inicial;
- categoria;
- palavra-chave;
- parâmetros de busca;
- configurações do projeto.

Essas informações devem ser obtidas por configuração, nunca codificadas diretamente.

---

# Saída

Todo scraper deve retornar exclusivamente uma coleção de objetos Oferta.

Exemplo conceitual:

```text
[
 Oferta,
 Oferta,
 Oferta,
 Oferta
]
```

Nenhum outro tipo de estrutura deve ser retornado.

---

# Tratamento de Erros

Cada scraper deve tratar falhas de forma isolada.

Exemplos:

- timeout;
- erro HTTP;
- CAPTCHA;
- estrutura HTML alterada;
- API indisponível.

O erro de um scraper não deve interromper a execução dos demais.

---

# Registro de Logs

Todo scraper deve registrar eventos relevantes.

Exemplos:

- início da execução;
- quantidade de ofertas encontradas;
- tempo de execução;
- falhas;
- exceções.

Logs devem ser informativos e suficientes para depuração.

---

# Estratégias de Coleta

Dependendo da fonte, diferentes estratégias podem ser utilizadas.

Exemplos:

## HTML

Utilização de Playwright ou Requests.

---

## API

Consumo direto de endpoints públicos ou privados.

---

## JSON Embutido

Extração de dados presentes na própria página.

---

## Renderização Dinâmica

Uso de Playwright quando o conteúdo depender de JavaScript.

---

# Seleção da Estratégia

A escolha da estratégia deve priorizar:

1. menor consumo de recursos;
2. maior estabilidade;
3. menor tempo de execução.

Sempre que possível deve-se preferir APIs ou HTML estático antes de utilizar navegadores automatizados.

---

# Normalização Inicial

Antes de criar uma Oferta, o scraper deve realizar normalizações básicas.

Exemplos:

- remover espaços extras;
- corrigir URLs;
- converter preços;
- remover caracteres inválidos.

Normalizações complexas pertencem ao pipeline.

---

# Independência

Cada scraper deve funcionar sem conhecer os demais.

Não deve existir comunicação entre scrapers.

Exemplo correto:

```text
Mercado Livre

Amazon

Kabum

Shopee
```

Todos executam de forma independente.

---

# Escalabilidade

A arquitetura suporta qualquer quantidade de scrapers.

```text
Mercado Livre

Amazon

Kabum

Terabyte

Pichau

Shopee

AliExpress

Magazine Luiza

Casas Bahia

...
```

Adicionar um novo scraper não deve exigir alterações estruturais.

---

# Boas Práticas

Cada scraper deve:

- herdar de BaseScraper;
- possuir uma única responsabilidade;
- produzir objetos Oferta;
- tratar exceções localmente;
- registrar logs;
- evitar duplicação de código;
- reutilizar componentes compartilhados.

---

# O que NÃO Fazer

Evite implementar nos scrapers:

- regras de negócio;
- cálculos comerciais;
- persistência;
- publicação;
- geração de mensagens;
- monetização;
- filtros.

Essas responsabilidades pertencem a outras camadas.

---

# Evolução Prevista

A arquitetura permite futuras melhorias como:

- execução paralela;
- filas de coleta;
- proxies;
- rotação de User-Agent;
- cache;
- limitação de taxa;
- retries automáticos;
- monitoramento de disponibilidade;
- coleta distribuída.

Nenhuma dessas evoluções deverá alterar a interface pública dos scrapers.

---

# Resumo

Os scrapers representam exclusivamente a camada de aquisição de dados do Projeto Renda Automática.

Sua responsabilidade termina quando os dados da fonte externa são convertidos em objetos `Oferta`.

Toda lógica de negócio, monetização, persistência e publicação ocorre nas etapas seguintes do pipeline.
