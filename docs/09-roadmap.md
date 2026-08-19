# Roadmap

> Este documento apresenta a evolução planejada para o Projeto Renda Automática, organizando funcionalidades por fases e prioridades.

---

# Objetivo

O Roadmap serve como guia de desenvolvimento do projeto.

Seu objetivo é organizar a evolução da aplicação de forma incremental, permitindo que novas funcionalidades sejam adicionadas sem comprometer a estabilidade do sistema.

Este documento representa a direção do projeto e poderá ser atualizado conforme novas necessidades surgirem.

---

# Princípios

O desenvolvimento seguirá os seguintes princípios:

- funcionalidades pequenas e incrementais;
- arquitetura antes de complexidade;
- estabilidade antes de novas funcionalidades;
- automação sempre que possível;
- documentação atualizada junto ao código.

---

# Situação Atual

Atualmente o projeto já possui:

- arquitetura modular;
- pipeline definido;
- sistema de scrapers;
- estrutura para bots;
- estrutura de configuração;
- documentação técnica;
- ambiente validado.

A partir desta base, as próximas fases concentram-se em aumentar a capacidade do sistema.

---

# Fase 1 — MVP

## Objetivo

Publicar automaticamente ofertas de uma fonte utilizando um único canal de publicação.

### Funcionalidades

- [ ] Scraper funcional.
- [ ] Pipeline completo.
- [ ] Filtros básicos.
- [ ] Publicação no Telegram.
- [ ] Registro de ofertas publicadas.
- [ ] Configuração por `.env`.
- [ ] Logs básicos.

### Resultado Esperado

O sistema deve conseguir executar todo o pipeline automaticamente.

---

# Fase 2 — Monetização

## Objetivo

Adicionar monetização às ofertas.

### Funcionalidades

- [ ] Sistema de afiliados.
- [ ] Registro de afiliadores.
- [ ] Geração automática de links.
- [ ] Suporte a múltiplas plataformas.

### Resultado Esperado

Toda oferta publicada deverá possuir link monetizado quando possível.

---

# Fase 3 — Qualidade

## Objetivo

Melhorar a qualidade das ofertas publicadas.

### Funcionalidades

- [ ] Sistema de pontuação.
- [ ] Histórico de preços.
- [ ] Curadoria automática.
- [ ] Classificação por categoria.
- [ ] Priorização de ofertas.

### Resultado Esperado

As publicações passam a privilegiar oportunidades realmente relevantes.

---

# Fase 4 — Escalabilidade

## Objetivo

Expandir o número de fontes e aumentar a capacidade do sistema.

### Funcionalidades

- [ ] Novos scrapers.
- [ ] Execução paralela.
- [ ] Controle de falhas.
- [ ] Retry automático.
- [ ] Cache.
- [ ] Limitação de requisições.

### Resultado Esperado

O sistema deverá suportar dezenas de fontes simultaneamente.

---

# Fase 5 — Persistência

## Objetivo

Evoluir o armazenamento.

### Funcionalidades

- [ ] SQLite.
- [ ] PostgreSQL.
- [ ] Migrações.
- [ ] Histórico completo.
- [ ] Estatísticas.

### Resultado Esperado

Maior confiabilidade e capacidade de análise dos dados.

---

# Fase 6 — Inteligência

## Objetivo

Adicionar mecanismos inteligentes ao pipeline.

### Funcionalidades

- [ ] Classificação automática.
- [ ] IA para categorização.
- [ ] IA para títulos.
- [ ] IA para descrição.
- [ ] IA para avaliação da qualidade.

### Resultado Esperado

Maior autonomia do sistema durante o processamento.

---

# Fase 7 — Publicação Multiplataforma

## Objetivo

Publicar simultaneamente em diferentes canais.

### Funcionalidades

- [ ] Discord.
- [ ] WhatsApp.
- [ ] X.
- [ ] Facebook.
- [ ] Instagram.
- [ ] API própria.

### Resultado Esperado

Uma única oferta poderá ser distribuída automaticamente para diversos canais.

---

# Fase 8 — Painel Administrativo

## Objetivo

Centralizar a administração do sistema.

### Funcionalidades

- [ ] Dashboard.
- [ ] Histórico.
- [ ] Configurações.
- [ ] Logs.
- [ ] Estatísticas.
- [ ] Controle de scrapers.

### Resultado Esperado

O projeto poderá ser administrado sem alterar o código.

---

# Fase 9 — Alta Escalabilidade

## Objetivo

Preparar o sistema para grandes volumes.

### Funcionalidades

- [ ] Filas.
- [ ] Workers.
- [ ] Processamento distribuído.
- [ ] Balanceamento.
- [ ] Cache distribuído.
- [ ] Monitoramento.

### Resultado Esperado

O sistema deverá suportar milhares de ofertas por execução.

---

# Fase 10 — Plataforma

## Objetivo

Transformar o projeto em uma plataforma reutilizável.

### Funcionalidades

- [ ] Sistema de plugins.
- [ ] API pública.
- [ ] Marketplace de extensões.
- [ ] SDK.
- [ ] Documentação para terceiros.

### Resultado Esperado

Novas funcionalidades poderão ser desenvolvidas sem modificar o núcleo da aplicação.

---

# Prioridades

As prioridades do projeto seguem a ordem:

1. Estabilidade.
2. Monetização.
3. Qualidade.
4. Escalabilidade.
5. Inteligência.
6. Plataforma.

Sempre que houver conflito entre estabilidade e novas funcionalidades, a estabilidade terá prioridade.

---

# Critérios de Conclusão

Uma fase será considerada concluída quando:

- todas as funcionalidades planejadas estiverem implementadas;
- os testes estiverem aprovados;
- a documentação estiver atualizada;
- o pipeline permanecer funcional.

---

# Funcionalidades Futuras

Ideias previstas para versões posteriores:

- comparação automática entre marketplaces;
- detecção de erro de preço;
- monitoramento de estoque;
- análise de tendências;
- alertas personalizados;
- suporte internacional;
- múltiplas moedas;
- tradução automática;
- recomendações por IA.

Essas funcionalidades permanecem fora do escopo atual, mas já são consideradas durante a evolução da arquitetura.

---

# Manutenção do Roadmap

Este documento deve ser revisado sempre que:

- uma fase for concluída;
- uma nova prioridade surgir;
- uma funcionalidade for removida;
- a direção do projeto mudar.

O Roadmap deve refletir o estado real do planejamento.

---

# Resumo

O Projeto Renda Automática será desenvolvido de forma incremental, priorizando estabilidade, organização e escalabilidade.

Cada nova funcionalidade deve aproximar o projeto da visão de longo prazo, preservando a arquitetura definida nos demais documentos da pasta `docs`.
