# 🚀 Radar de Ofertas

> Um sistema inteligente para descobrir ofertas, gerar links de afiliados automaticamente e publicar promoções de forma automatizada.

<p align="center">

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-orange?style=for-the-badge)
![GitHub](https://img.shields.io/github/last-commit/Kausjh/ProjetoRendaAutomatica?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

</p>

---

## 📖 Sobre o projeto

O **Radar de Ofertas** é um sistema desenvolvido para automatizar todo o processo de descoberta e publicação de ofertas de produtos.

O objetivo é transformar um fluxo totalmente manual em um pipeline automatizado:

- encontrar ofertas;
- analisar sua qualidade;
- gerar links de afiliados;
- preparar a publicação;
- enviar automaticamente para o Telegram.

O projeto foi construído priorizando arquitetura limpa, baixo acoplamento e facilidade para expansão.

---

# ⚙️ Fluxo do sistema

```text
Marketplaces

(Mercado Livre, Amazon, Shopee...)

        │
        ▼

Coleta de Produtos
    (Scrapers)

        │
        ▼

Normalização

        │
        ▼

Filtros

        │
        ▼

Histórico de Preços

        │
        ▼

Pontuação Comercial

        │
        ▼

Links de Afiliados

        │
        ▼

Formatação

        │
        ▼

Telegram
```

---

# ✨ Funcionalidades

- ✅ Arquitetura modular
- ✅ Sistema de Scrapers
- ✅ Filtros inteligentes
- ✅ Histórico de preços
- ✅ Pontuação automática de ofertas
- ✅ Integração com Telegram
- ✅ Integração com Mercado Livre
- ✅ Cache de links afiliados
- ✅ Reutilização automática de links

---

# 🏗 Estrutura

```text
ProjetoRendaAutomatica/

├── bots/
├── config/
├── database/
├── filters/
├── formatters/
├── models/
├── repositories/
├── scrapers/
├── services/
├── scripts/
├── tests/
├── main.py
└── README.md
```

---

# 🛠 Tecnologias

- Python
- Playwright
- HTTPX
- Telegram Bot API
- JSON
- Git
- GitHub

---

# 🚀 Instalação

Clone o projeto:

```bash
git clone https://github.com/Kausjh/ProjetoRendaAutomatica.git
```

Entre na pasta:

```bash
cd ProjetoRendaAutomatica
```

Crie o ambiente virtual:

```bash
python -m venv .venv
```

Ative o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

---

# ▶️ Executando

```bash
python main.py
```

---

# 🗺 Roadmap

## ✅ Concluído

- Arquitetura inicial
- Sistema de Scrapers
- Sistema de Filtros
- Histórico de preços
- Pontuação de ofertas
- Integração com Telegram
- Integração com Mercado Livre
- Cache de links afiliados

---

## 🚧 Em desenvolvimento

- Pipeline completo Mercado Livre → Telegram
- Melhorias comerciais
- Curadoria automática

---

## 🔮 Futuro

- Amazon Associates
- Shopee
- KaBuM
- Pichau
- Terabyte
- SQLite
- Dashboard Web
- Docker
- API REST

---

# 👨‍💻 Autor

**Radar de Ofertas**

> "Automatizar o trabalho repetitivo para dedicar tempo ao que realmente importa."