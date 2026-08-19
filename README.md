Projeto Renda Automática

Plataforma modular para descoberta, análise, monetização e publicação automática de oportunidades comerciais utilizando programas de afiliados.



Visão Geral

O Projeto Renda Automática foi desenvolvido com um objetivo simples:

Encontrar boas ofertas automaticamente, transformá-las em links de afiliados e publicá-las sem intervenção manual.

Mas esse é apenas o ponto de partida.

O verdadeiro objetivo é construir uma plataforma capaz de automatizar todo o ciclo de vida de uma oportunidade comercial: descoberta, análise, enriquecimento, monetização e distribuição.

A arquitetura foi pensada para crescer continuamente. Novos marketplaces, programas de afiliados, estratégias de classificação e canais de publicação podem ser adicionados sem reescrever o núcleo do sistema.

Como o sistema funciona

Marketplace

        │

        ▼

Scraper

        │

        ▼

Oferta

        │

        ▼

Pipeline

        │

        ├── Normalização

        ├── Validação

        ├── Curadoria

        ├── Histórico

        ├── Classificação

        ├── Pontuação

        ├── Monetização

        └── Formatação

        │

        ▼

Publicação

Toda a aplicação gira em torno da entidade Oferta.

O pipeline apenas a enriquece progressivamente até que esteja pronta para publicação.

Arquitetura

┌──────────────────────────────┐
│          Scrapers            │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│          Services            │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│          Filters             │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│       Repositories           │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│            Bots              │
└──────────────────────────────┘

Cada camada possui apenas uma responsabilidade. Isso permite evolução incremental, baixo acoplamento e facilidade para testes.

Estrutura do Projeto

ProjetoRendaAutomatica/

├── bots/
├── config/
├── database/
├── docs/
├── filters/
├── formatters/
├── models/
├── repositories/
├── scrapers/
├── services/
├── tests/

├── main.py
├── pyproject.toml
├── README.md
└── .env.example

Funcionalidades

Coleta automática de ofertas

Múltiplos scrapers

Pipeline completo de processamento

Curadoria comercial

Histórico de preços

Sistema de pontuação

Monetização por afiliados

Publicação automática

Arquitetura modular

Configuração externa

Pipeline Oficial

Coleta
↓
Normalização
↓
Validação
↓
Filtragem
↓
Classificação
↓
Pontuação
↓
Monetização (Afiliados)
↓
Formatação
↓
Publicação
↓
Persistência

Tecnologias

Python 3.11+

Playwright

Requests

Telegram Bot API

JSON

Pytest

Ruff

MyPy

Git

GitHub

Instalação

Consulte:

docs/07-instalacao.md

Documentação

A documentação técnica completa encontra-se em docs/.

Arquitetura

Pipeline

Modelo de Domínio

Sistema de Afiliados

Scrapers

Configuração

Instalação

Decisões Arquiteturais

Roadmap

Stack Tecnológica

Princípios

Responsabilidade única

Baixo acoplamento

Alta coesão

Arquitetura modular

Código extensível

Configuração centralizada

Evolução incremental

Roadmap

Próximos objetivos:

Amazon

Shopee

Kabum

Pichau

Dashboard Web

IA para classificação

Estatísticas

Banco de dados

Múltiplos canais de publicação

Contribuindo

Antes de implementar uma funcionalidade, pergunte:

Em qual camada ela pertence?

Ela aumenta o acoplamento?

Pode ser reutilizada?

A documentação precisa ser atualizada?

Licença

Este projeto é distribuído sob a licença MIT.

Autor

Kauê Jhonatas

Projeto desenvolvido com foco em automação comercial, engenharia de software e arquitetura modular.

Filosofia

O Projeto Renda Automática não é apenas um scraper.

Ele é uma plataforma para descoberta, análise, monetização e distribuição automatizada de oportunidades comerciais.

Toda evolução do projeto deve preservar essa ideia.

O objetivo não é apenas publicar ofertas.

O objetivo é construir uma plataforma capaz de crescer continuamente sem perder organização, simplicidade e qualidade arquitetural.
