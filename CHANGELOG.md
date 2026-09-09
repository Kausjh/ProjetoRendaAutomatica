<!-- 63.8738, -149.7525 -->

# Changelog

Todas as mudanças relevantes deste projeto são documentadas neste arquivo.

O formato é inspirado no padrão [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e segue, quando aplicável, os princípios de Versionamento Semântico (SemVer).

---

# [Unreleased]

## Adicionado

- README público reescrito para refletir o estado real do projeto na V10.
- Documentação arquitetural atualizada com os fluxos de coleta própria e Social Scout.
- Stack tecnológica revisada com os componentes atuais de runtime, persistência, browser automation, testes e operação.
- Proteções adicionais no `.gitignore` para arquivos laterais de sessão Telegram (`*.session-shm` e `*.session-wal`).

## Alterado

- Documentação pública sincronizada com o comportamento atual do pipeline.
- Roadmap atualizado para a direção de Canonical Catalog, Price Intelligence, Alert Engine, API e aplicações cliente.
- Itens antigos de planejamento que já foram implementados deixaram de ser apresentados como trabalho futuro.

## Planejado

- Suporte Amazon no Social Scout.
- Canonical Catalog para unificar identidades de produto entre marketplaces.
- Price Intelligence com histórico consolidado e comparação entre lojas.
- Alert Engine.
- API própria.
- Aplicações cliente, incluindo app, web e extensão de navegador.
- Avaliação e integração futura de novos parceiros e marketplaces, incluindo Pichau e TerabyteShop.

---

# [1.4.0] - 2026-09

## Adicionado

- Social Scout como fonte passiva de inteligência a partir de uma conta Telegram autorizada.
- Detector de mensagens para distinguir ofertas de produto, cupons e conteúdo irrelevante.
- Processamento persistente do Social Scout com SQLite.
- Fingerprints de processamento.
- Estados transitórios e terminais.
- Política de retry com cooldown e TTL.
- Handoff durável para reduzir perda de trabalho entre processamento e confirmação.
- Shadow Mode para executar o pipeline real sem liberar automaticamente toda decisão para publicação.
- Observabilidade baseada em agregados, sem necessidade de expor payloads ou identificadores privados.
- Allowlist própria de categorias para o Social Scout.
- Proteção específica contra falsos positivos de CPU.
- Supervisor operacional para Windows.
- Recuperação automática de runtime, listener e Chrome/CDP.
- Integração do Social Scout com Mercado Livre.
- Integração do Social Scout com Shopee.
- Integração do Social Scout com AliExpress.
- Integração do Social Scout com KaBuM!.
- Resolução conservadora de múltiplos links Shopee.
- Resolução de identidade AliExpress por destino exato de produto.
- Resolução de links `tidd.ly` por destino real antes de atribuir KaBuM!.
- Validação KaBuM! por identidade exata e dados estruturados JSON-LD.
- Cooldown persistente para desafio humano na KaBuM!.
- Coleta nativa de candidatos AliExpress através de feed de afiliados Awin.
- Tratamento de indisponibilidade regional e desafios humanos no fluxo AliExpress.

## Melhorado

- O Social Scout passou a preferir identidade verificável a inferências por título.
- Mensagens externas passaram a ser tratadas como pistas, e não como fonte absoluta de verdade.
- Validação de preço passou a rejeitar divergências e estados não verificáveis de forma conservadora.
- Processamento de backlog foi ajustado para evitar starvation.
- Falhas transitórias passaram a poder ser reprocessadas dentro de janelas controladas.
- Mudanças de fingerprint passaram a permitir nova avaliação de mensagens modificadas.
- Escopo de produtos passou a operar em modo fail-closed.
- O tratamento de múltiplos links deixou de escolher arbitrariamente o primeiro destino.
- Integrações com navegador passaram a respeitar cooldowns e desafios humanos sem tentativa de bypass.

## Corrigido

- Falsos positivos em que produtos fora do nicho podiam ser classificados como hardware.
- Caso real de um mini processador de alimentos classificado semanticamente como `Processador`.
- Estados de preço não verificável que poderiam ser tratados incorretamente como falhas transitórias.
- Reprocessamento excessivo de estados que deveriam respeitar cooldown.
- Possibilidade de starvation do backlog do Social Scout.
- Ambiguidades de identidade em mensagens com múltiplos produtos.
- Tratamento de destinos não-produto em links de AliExpress e KaBuM!.

## Qualidade

- Suíte de testes expandida continuamente ao longo das versões do Social Scout.
- Snapshot da V10 validado com **562 testes aprovados**.
- Validações de pre-commit mantidas com Black, Ruff e hooks de integridade de arquivos.

## Segurança

- Sessões Telegram, credenciais, perfis de navegador e bancos locais permanecem fora do repositório público.
- O listener do Social Scout opera de forma passiva.
- Desafios humanos são detectados e respeitados; o projeto não implementa bypass de CAPTCHA.

---

# [1.3.0] - 2026-07

## Adicionado

- Arquitetura modular para afiliadores.
- Registro automático de afiliadores.
- Carregador automático de afiliadores.
- Geração automática de links afiliados.
- Publicação automática no Telegram.
- Pipeline de processamento centralizado.
- Documentação técnica completa.

## Melhorado

- Organização das camadas do projeto.
- Separação entre regras de negócio e persistência.
- Estrutura de diretórios.
- Organização do pipeline.

---

# [1.2.0] - 2026-07

## Adicionado

- Integração funcional com Mercado Livre.
- Geração de links monetizados.
- Persistência de ofertas publicadas.
- Sistema de pontuação inicial.

## Corrigido

- Problemas na geração de links.
- Tratamento de ofertas duplicadas.
- Melhorias na formatação das mensagens.

---

# [1.1.0] - 2026-07

## Adicionado

- Pipeline de execução.
- Sistema de Scrapers.
- BaseScraper.
- Modelo Oferta.
- Serviços de Curadoria.
- Sistema de Formatação.

## Melhorado

- Organização dos serviços.
- Reutilização de código.
- Estrutura dos módulos.

---

# [1.0.0] - 2026-07

## Adicionado

Primeira versão funcional do Projeto Renda Automática.

Características iniciais:

- Coleta automática de ofertas.
- Estrutura modular.
- Publicação automática.
- Configuração via `.env`.
- Organização em camadas.

---

# Convenções

## Adicionado

Novas funcionalidades.

## Alterado

Mudanças em funcionalidades existentes.

## Melhorado

Aprimoramentos sem alteração de comportamento principal.

## Corrigido

Correções de bugs.

## Removido

Funcionalidades removidas.

## Segurança

Correções relacionadas à segurança.

## Depreciado

Funcionalidades que serão removidas futuramente.
