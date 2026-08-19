# Instalação

> Este documento descreve todo o processo de instalação, configuração e validação do ambiente de desenvolvimento do Projeto Renda Automática.

---

# Objetivo

O objetivo deste documento é permitir que qualquer desenvolvedor consiga preparar um ambiente funcional do projeto de forma rápida, reproduzível e padronizada.

Ao final deste guia será possível:

- executar o projeto;
- executar os testes;
- validar a instalação;
- iniciar o desenvolvimento.

---

# Requisitos

O projeto foi validado utilizando:

| Ferramenta | Versão Validada |
|------------|-----------------|
| Python | 3.13.14 |
| Git | Atual |
| Playwright | Instalado |
| Chromium | Instalado pelo Playwright |
| pip | Atualizado |

> **Compatibilidade:** o projeto exige **Python 3.11 ou superior** (`requires-python >=3.11`). A versão atualmente validada é **3.13.14**.

---

# Estrutura Esperada

Após clonar o repositório, a estrutura deverá ser semelhante a:

```text
ProjetoRendaAutomatica/

│
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
├── .venv/
├── .env
├── .env.example
├── pyproject.toml
└── README.md
```

---

# 1. Clonar o Projeto

```bash
git clone <URL_DO_REPOSITORIO>
```

Entrar na pasta:

```bash
cd ProjetoRendaAutomatica
```

---

# 2. Criar Ambiente Virtual

Windows

```powershell
python -m venv .venv
```

Linux

```bash
python3 -m venv .venv
```

---

# 3. Ativar Ambiente Virtual

Windows

```powershell
.venv\Scripts\activate
```

Linux

```bash
source .venv/bin/activate
```

Após ativar, o terminal deverá exibir algo semelhante a:

```text
(.venv)
```

---

# 4. Atualizar o pip

```bash
python -m pip install --upgrade pip
```

---

# 5. Instalar Dependências

Caso exista:

```bash
pip install -e .
```

ou

```bash
pip install -r requirements.txt
```

Dependendo da estratégia utilizada pelo projeto.

---

# 6. Instalar Playwright

```bash
playwright install chromium
```

Caso o Playwright já esteja instalado, este comando apenas verificará os componentes necessários.

---

# 7. Configurar Variáveis de Ambiente

Criar o arquivo:

```text
.env
```

a partir do exemplo:

```text
.env.example
```

Preencher todas as variáveis obrigatórias.

Exemplo:

```text
TELEGRAM_TOKEN=

TELEGRAM_CHAT_ID=
```

Nunca envie o arquivo `.env` para o repositório.

---

# 8. Validar a Instalação

Verificar a versão do Python:

```bash
python --version
```

Resultado esperado:

```text
Python 3.13.14
```

---

Verificar o ambiente virtual:

```bash
where python
```

O caminho deve apontar para:

```text
.venv
```

---

# 9. Executar os Testes

```bash
pytest
```

Resultado esperado:

```text
Todos os testes devem ser aprovados.
```

Caso algum teste falhe, o ambiente deve ser corrigido antes do desenvolvimento.

---

# 10. Executar o Ruff

```bash
ruff check .
```

Resultado esperado:

```text
O Ruff não deve reportar erros.
```

---

# 11. Executar o MyPy

```bash
mypy .
```

Atualmente existe uma limitação conhecida relacionada à duplicação do módulo `automation_web`.

Essa situação encontra-se documentada e deverá ser corrigida futuramente.

Até essa correção, esse erro é esperado.

---

# 12. Executar o Projeto

Com o ambiente preparado:

```bash
python main.py
```

ou o comando oficial definido pelo projeto.

O sistema deverá iniciar sem erros de configuração.

---

# Estrutura Recomendada do Ambiente

```text
Windows 10/11

↓

Python 3.13+

↓

Virtual Environment (.venv)

↓

Dependências

↓

Playwright

↓

Projeto
```

---

# Solução de Problemas

## Playwright não inicia

Execute novamente:

```bash
playwright install chromium
```

---

## Ambiente Virtual Incorreto

Verifique:

```bash
where python
```

O executável deve estar dentro da pasta `.venv`.

---

## Dependências Quebradas

Execute:

```bash
pip check
```

Resultado esperado:

```text
No broken requirements found.
```

---

## Erro de MyPy

Se o erro estiver relacionado ao módulo:

```text
automation_web
```

trata-se de uma limitação conhecida da estrutura atual do projeto.

---

# Atualização das Dependências

Sempre que novas dependências forem adicionadas:

1. atualizar o arquivo de dependências;
2. atualizar este documento, se necessário;
3. validar novamente o ambiente utilizando os comandos anteriores.

---

# Checklist de Instalação

Antes de iniciar o desenvolvimento, confirme:

- [ ] Repositório clonado.
- [ ] Ambiente virtual criado.
- [ ] Ambiente virtual ativado.
- [ ] Dependências instaladas.
- [ ] Chromium instalado.
- [ ] Arquivo `.env` criado.
- [ ] Variáveis preenchidas.
- [ ] Testes executados.
- [ ] Ruff sem erros.
- [ ] Projeto inicia normalmente.

---

# Atualização deste Documento

Este documento deve ser atualizado sempre que ocorrer uma alteração em:

- versão mínima do Python;
- ferramenta de build;
- processo de instalação;
- dependências obrigatórias;
- estrutura do ambiente.

---

# Resumo

Um ambiente corretamente configurado deve permitir que qualquer desenvolvedor execute o Projeto Renda Automática utilizando apenas os passos descritos neste documento.

Qualquer procedimento adicional necessário para iniciar o projeto deve ser documentado aqui.
