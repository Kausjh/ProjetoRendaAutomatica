# Arquitetura dos Scrapers

> Este documento descreve a camada responsável pela coleta de dados dos marketplaces.

---

# Objetivo

A função dos scrapers é simples:

**Transformar páginas de marketplaces em objetos `Oferta`.**

Nada mais.

Os scrapers não possuem responsabilidade sobre:

- monetização;
- classificação;
- filtros;
- Telegram;
- histórico;
- persistência;
- pontuação.

Eles apenas coletam dados.

---

# Papel na Arquitetura

```
Marketplace

↓

Scraper

↓

Oferta

↓

Pipeline
```

Os scrapers representam a porta de entrada de todo o sistema.

Toda informação utilizada posteriormente nasce aqui.

---

# Estrutura

```
scrapers/

├── base_scraper.py
├── mercado_livre/
├── ...
```

Todos os scrapers devem seguir a mesma estrutura.

---

# BaseScraper

Todo scraper deve herdar de `BaseScraper`.

Ela define o contrato mínimo esperado pelo restante da aplicação.

Isso garante que qualquer marketplace possa ser integrado sem alterar o pipeline.

---

# Responsabilidades

Cada scraper deve ser responsável apenas por:

- acessar a fonte de dados;
- localizar os produtos;
- extrair as informações;
- construir objetos `Oferta`;
- devolver uma lista de ofertas.

---

# O que um scraper NÃO deve fazer

Nunca:

- enviar mensagens;
- gerar links afiliados;
- consultar histórico;
- salvar arquivos;
- aplicar filtros comerciais;
- decidir se uma oferta é boa;
- acessar Telegram.

Essas responsabilidades pertencem às demais camadas.

---

# Fluxo de Execução

```
Marketplace

↓

Requisição

↓

Resposta

↓

Extração

↓

Oferta

↓

Lista de Ofertas

↓

Pipeline
```

---

# Dados mínimos esperados

Uma Oferta criada por um scraper deve conter, sempre que possível:

- nome;
- preço;
- preço anterior;
- URL;
- loja;
- imagem;
- categoria;
- marketplace de origem.

Quanto mais completa for a coleta, melhor será o restante do pipeline.

---

# Tratamento de Erros

Um scraper nunca deve interromper a execução do sistema inteiro.

Caso ocorra erro:

- registrar o problema;
- ignorar a oferta inválida quando possível;
- permitir que os demais scrapers continuem funcionando.

A falha de um marketplace não deve impedir a coleta dos demais.

---

# Independência

Cada scraper deve funcionar isoladamente.

Isso significa que:

- não deve depender de outro scraper;
- não deve conhecer outros marketplaces;
- não deve compartilhar lógica específica.

Todo comportamento compartilhado deve estar em `BaseScraper` ou em componentes reutilizáveis.

---

# Adicionando um Novo Scraper

O processo recomendado é:

1. Criar uma nova classe herdando de `BaseScraper`.
2. Implementar a coleta dos produtos.
3. Converter os dados para objetos `Oferta`.
4. Registrar o scraper no sistema.
5. Validar o funcionamento de forma isolada.

Nenhuma alteração deve ser necessária nas demais camadas.

---

# Princípios

A camada de coleta segue os princípios:

- responsabilidade única;
- baixo acoplamento;
- alta coesão;
- independência entre marketplaces;
- reutilização através da classe base.

---

# Boas Práticas

Sempre que possível:

- reutilizar sessões HTTP;
- evitar requisições duplicadas;
- respeitar limites das plataformas;
- tratar mudanças de layout de forma resiliente;
- registrar erros úteis para depuração;
- manter a lógica de parsing separada da lógica de negócio.

---

# Relação com o Pipeline

O scraper é apenas o primeiro estágio do processo.

Após criar as ofertas, ele entrega totalmente o controle para o pipeline.

```
Scraper

↓

Oferta

↓

Pipeline

↓

Filtros

↓

Curadoria

↓

Histórico

↓

Pontuação

↓

Afiliador

↓

Formatter

↓

Telegram
```

A partir desse momento o scraper não participa mais da execução.

---

# Conclusão

Os scrapers existem para uma única finalidade: **coletar dados de forma consistente e produzir objetos `Oferta`.**

Ao manter essa responsabilidade isolada, a arquitetura permanece simples, extensível e preparada para integrar qualquer novo marketplace sem impacto nas demais partes do sistema.
