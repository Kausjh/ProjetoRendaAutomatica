# Roadmap

> Este documento define a direção de evolução do Projeto Renda Automática.
>
> O objetivo não é listar ideias aleatórias, mas organizar o desenvolvimento em etapas lógicas, priorizando impacto, estabilidade e escalabilidade.

---

# Filosofia

Antes de adicionar novas funcionalidades, o sistema deve permanecer:

- estável;
- previsível;
- modular;
- fácil de manter.

Cada nova funcionalidade deve fortalecer a arquitetura existente, e nunca contorná-la.

---

# Situação Atual

Atualmente o projeto já possui:

- Arquitetura modular;
- Pipeline de processamento;
- Camada de scrapers;
- Camada de afiliados;
- Sistema de formatação;
- Persistência;
- Publicação no Telegram;
- Documentação técnica.

Essa base é suficiente para evoluir com segurança.

---

# Fase 1 — Consolidação

Objetivo:

Transformar o projeto em uma plataforma sólida.

## Tarefas

- [ ] Revisar toda a documentação
- [ ] Melhorar o README
- [ ] Revisar nomes de módulos
- [ ] Padronizar logs
- [ ] Padronizar tratamento de erros
- [ ] Melhorar mensagens de inicialização
- [ ] Criar suíte de testes

---

# Fase 2 — Novos Marketplaces

Adicionar novos scrapers.

## Prioridade

- [ ] Amazon
- [ ] Shopee
- [ ] Kabum
- [ ] Pichau
- [ ] Terabyte
- [ ] Magazine Luiza
- [ ] AliExpress

Objetivo:

Aumentar significativamente o número de oportunidades coletadas.

---

# Fase 3 — Novos Programas de Afiliados

Expandir a monetização.

## Meta

Cada marketplace suportado deve possuir integração própria.

---

# Fase 4 — Inteligência Comercial

Adicionar mecanismos para selecionar automaticamente as melhores ofertas.

Possíveis recursos:

- histórico de preços;
- tendência de preço;
- frequência de promoções;
- reputação da loja;
- relevância do produto.

---

# Fase 5 — IA

Aplicar Inteligência Artificial em partes específicas do pipeline.

Exemplos:

- classificação automática;
- categorização;
- criação de títulos;
- geração de descrições;
- identificação de erros de preço;
- priorização de ofertas.

---

# Fase 6 — Múltiplos Canais

Hoje:

```
Telegram
```

Objetivo:

```
Telegram

Discord

WhatsApp

X (Twitter)

Facebook

Instagram

Threads

RSS
```

O pipeline deve publicar para qualquer canal.

---

# Fase 7 — Painel Administrativo

Criar uma interface para acompanhar o funcionamento da aplicação.

Possíveis recursos:

- ofertas coletadas;
- ofertas publicadas;
- erros;
- histórico;
- estatísticas;
- afiliadores ativos;
- scrapers ativos.

---

# Fase 8 — Estatísticas

Criar métricas de desempenho.

Exemplos:

- ofertas por dia;
- taxa de aprovação;
- tempo médio de processamento;
- marketplace mais eficiente;
- categoria mais lucrativa.

---

# Fase 9 — Arquitetura

Melhorias estruturais previstas.

## ExecutorPipeline

Transformá-lo em um orquestrador simples.

---

## Pipeline Modular

Migrar completamente para a infraestrutura baseada em etapas.

---

## Injeção de Dependências

Centralizar toda composição da aplicação.

---

## Testes

Cobertura automatizada.

---

# Fase 10 — Escalabilidade

Preparar o projeto para crescimento.

Possíveis melhorias:

- filas;
- processamento paralelo;
- múltiplos workers;
- cache distribuído;
- banco de dados dedicado.

---

# Melhorias Técnicas

Lista contínua.

- [ ] Melhorar tipagem
- [ ] Cobertura de testes
- [ ] Melhorar logs
- [ ] Melhorar tratamento de exceções
- [ ] Melhorar documentação
- [ ] Revisar dependências
- [ ] Automatizar validações

---

# Melhorias de Negócio

- [ ] Mais programas de afiliados
- [ ] Mais marketplaces
- [ ] Mais canais
- [ ] Melhor curadoria
- [ ] Melhor classificação
- [ ] Melhor monetização

---

# Longo Prazo

Transformar o Projeto Renda Automática em uma plataforma completa de inteligência comercial.

Características esperadas:

- coleta automatizada;
- análise de ofertas;
- enriquecimento de dados;
- monetização;
- distribuição multicanal;
- métricas;
- painel administrativo;
- escalabilidade horizontal.

---

# Critérios para Novas Funcionalidades

Antes de iniciar qualquer desenvolvimento, responder:

1. Qual problema será resolvido?
2. Em qual camada essa responsabilidade pertence?
3. Existe reutilização possível?
4. Essa mudança aumenta ou reduz o acoplamento?
5. O pipeline continuará simples?
6. A documentação precisará ser atualizada?

Se a resposta não estiver clara, a implementação deve ser reavaliada.

---

# Objetivo Final

Construir uma plataforma robusta, modular e escalável para descoberta, análise, monetização e distribuição automática de oportunidades comerciais, capaz de evoluir continuamente sem perder organização arquitetural.
