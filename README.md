# 🚀 Projeto Renda Automática

> Sistema modular para encontrar ofertas, validá-las, gerar links de afiliado e publicá-las automaticamente no Telegram.

---

## 📖 Sobre o projeto

O Projeto Renda Automática nasceu com um único objetivo:

> Construir uma plataforma capaz de gerar renda recorrente através da divulgação automática de ofertas.

O sistema coleta produtos de diversos marketplaces, identifica boas oportunidades, valida a qualidade das ofertas, gera links de afiliado e publica automaticamente em um canal do Telegram.

A arquitetura foi projetada para ser escalável, permitindo adicionar novos marketplaces e programas de afiliados sem alterar o restante do sistema.

---

# 🎯 Objetivos

- Encontrar ofertas automaticamente
- Validar se a oferta realmente vale a pena
- Evitar ofertas duplicadas
- Classificar ofertas por qualidade
- Gerar links de afiliado automaticamente
- Publicar no Telegram
- Escalar para diversos marketplaces

---

# 🏗 Arquitetura

```text
                ┌──────────────┐
                │   Scrapers   │
                └──────┬───────┘
                       │
                       ▼
             Coletor de Ofertas
                       │
                       ▼
             Validador de Ofertas
                       │
                       ▼
          Sistema de Classificação
                       │
                       ▼
            Gerador de Links
               de Afiliado
                       │
                       ▼
             Formatador da Mensagem
                       │
                       ▼
                Telegram Bot
```

---

# 📂 Estrutura do projeto

```text
ProjetoRendaAutomatica/

├── affiliates/
├── automation_web/
├── config/
├── database/
├── filters/
├── formatters/
├── launcher/
├── models/
├── repositories/
├── scrapers/
├── services/
├── telegram/
├── utils/
│
├── launcher.py
├── iniciar_projeto.bat
├── main.py
└── README.md
```

---

# ⚙ Funcionalidades

## ✅ Implementadas

- Launcher automático
- Inicialização simplificada
- Chrome com CDP
- Perfil persistente do navegador
- Coletor de ofertas
- Validador de ofertas
- Histórico de ofertas
- Estrutura de afiliados
- Integração Telegram
- Arquitetura modular
- Suporte ao Playwright

---

# 🛒 Marketplaces

## Implementados

- Mercado Livre

## Em desenvolvimento

- KaBuM

## Planejados

- Amazon
- Pichau
- Terabyte
- Shopee
- AliExpress

---

# 💰 Programas de afiliados

Planejados ou já suportados pela arquitetura:

- Mercado Livre Afiliados
- Amazon Associados
- KaBuM Partners
- Pichau
- Terabyte
- Shopee

---

# ▶ Como executar

## Clone

```bash
git clone https://github.com/Kausjh/ProjetoRendaAutomatica.git
```

---

## Ambiente virtual

```bash
python -m venv .venv
```

---

## Ativar

Windows

```bash
.venv\Scripts\activate
```

Linux

```bash
source .venv/bin/activate
```

---

## Instalar dependências

```bash
pip install -r requirements.txt
```

---

## Executar

Modo recomendado

```bash
python launcher.py
```

ou

```bash
iniciar_projeto.bat
```

---

# 🧠 Tecnologias

- Python
- Playwright
- Telegram Bot API
- Git
- GitHub

---

# 📌 Roadmap

## Concluído

- [x] Estrutura inicial
- [x] Pipeline modular
- [x] Launcher automático
- [x] Perfil persistente
- [x] Validador de ofertas
- [x] Integração Mercado Livre
- [x] Estrutura de afiliados

---

## Em desenvolvimento

- [ ] KaBuM
- [ ] Amazon
- [ ] Melhor classificação de ofertas
- [ ] Melhor sistema de pontuação

---

## Futuro

- [ ] Dashboard Web
- [ ] IA para análise de ofertas
- [ ] Estatísticas de conversão
- [ ] Múltiplos canais Telegram
- [ ] Interface gráfica

---

# 🤝 Contribuindo

Toda contribuição é bem-vinda.

Caso encontre bugs ou tenha sugestões, abra uma Issue.

Caso deseje implementar melhorias, envie um Pull Request.

---

# 📜 Licença

Este projeto encontra-se em desenvolvimento.

A licença definitiva será definida futuramente.

---

# 👨‍💻 Autor

**Radar de Ofertas**

Projeto desenvolvido com foco em automação, programação e geração de renda através de sistemas inteligentes.

---

## ⭐ Se este projeto te ajudar

Considere deixar uma estrela no repositório.

Isso ajuda bastante no crescimento do projeto.