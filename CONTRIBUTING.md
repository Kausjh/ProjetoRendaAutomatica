# Guia de Contribuição

Antes de tudo, obrigado pelo interesse em contribuir com o Projeto Renda Automática.

Este projeto foi desenvolvido com foco em arquitetura modular, baixo acoplamento e facilidade de evolução. Toda contribuição deve preservar esses princípios.

---

# Filosofia

O objetivo deste projeto não é apenas coletar ofertas.

O objetivo é construir uma plataforma de inteligência comercial capaz de crescer continuamente sem perder organização.

Sempre prefira:

- simplicidade;
- legibilidade;
- reutilização;
- baixo acoplamento.

---

# Estrutura do Projeto

```
ProjetoRendaAutomatica/

├── affiliates/
├── config/
├── database/
├── docs/
├── filters/
├── formatters/
├── models/
├── repositories/
├── scrapers/
├── services/
```

Cada pasta possui uma responsabilidade específica.

Nunca adicione funcionalidades em uma camada que não pertence a ela.

---

# Responsabilidades

## Scrapers

Responsáveis apenas por coletar informações.

Não devem:

- publicar mensagens;
- gerar links afiliados;
- salvar arquivos;
- tomar decisões comerciais.

---

## Models

Representam entidades do domínio.

Devem conter apenas informações relacionadas ao modelo.

---

## Services

Toda regra de negócio pertence aqui.

Exemplos:

- classificação;
- pontuação;
- curadoria;
- processamento;
- pipeline.

---

## Repositories

Responsáveis apenas pela persistência de dados.

Não devem conter regras de negócio.

---

## Formatters

Responsáveis apenas pela apresentação.

Nunca devem alterar a lógica da aplicação.

---

## Affiliates

Responsáveis exclusivamente pela monetização.

Cada programa de afiliados deve possuir sua própria implementação.

---

# Antes de criar código novo

Sempre responda:

- Esse código já existe em outro lugar?
- Posso reutilizar alguma classe?
- Em qual camada essa responsabilidade pertence?
- Estou aumentando o acoplamento?

Se existir dúvida, pare e revise a arquitetura antes de continuar.

---

# Adicionando um novo Scraper

Todo novo scraper deve:

- herdar da classe base;
- retornar objetos `Oferta`;
- não conter regras comerciais;
- não conhecer Telegram;
- não conhecer afiliadores.

---

# Adicionando um novo Afiliador

Cada integração deve:

- implementar a interface/base utilizada pelo projeto;
- ser registrada no sistema de afiliadores;
- não modificar o pipeline existente.

O restante da aplicação não deve precisar conhecer detalhes da implementação.

---

# Estilo de Código

Priorize:

- funções pequenas;
- nomes claros;
- baixo nível de complexidade;
- responsabilidade única;
- tipagem quando possível.

Evite:

- funções gigantes;
- duplicação;
- variáveis com nomes genéricos;
- comentários que expliquem o óbvio.

Prefira escrever código que seja autoexplicativo.

---

# Commits

Utilize mensagens objetivas.

Exemplos:

```
feat: adiciona scraper da Amazon

fix: corrige geração de links do Mercado Livre

refactor: simplifica ExecutorPipeline

docs: adiciona documentação do pipeline

test: adiciona testes para Oferta
```

---

# Pull Requests

Uma Pull Request deve:

- resolver um único problema;
- possuir descrição clara;
- não misturar refatoração com novas funcionalidades;
- manter a documentação atualizada quando necessário.

---

# Testes

Toda alteração importante deve ser validada antes do merge.

Sempre que possível:

- teste manualmente;
- execute a suíte de testes;
- valide o fluxo completo do pipeline.

---

# Documentação

Mudanças arquiteturais exigem atualização da documentação.

Arquivos relevantes:

```
docs/01-arquitetura.md

docs/02-pipeline.md

docs/03-modelo-de-dominio.md

docs/08-decisoes-de-arquitetura.md

docs/09-roadmap.md
```

A documentação deve refletir o estado atual do projeto.

---

# O que evitar

Evite:

- dependências circulares;
- lógica duplicada;
- regras de negócio em Scrapers;
- regras de negócio em Repositories;
- código morto;
- comentários desatualizados;
- acoplamento desnecessário.

---

# Qualidade acima de velocidade

Novas funcionalidades são importantes.

Mas preservar a arquitetura é mais importante ainda.

Uma implementação simples, organizada e consistente vale mais do que uma implementação complexa entregue rapidamente.

---

# Obrigado

Toda contribuição que respeitar estes princípios será muito bem-vinda.

Bom código!
