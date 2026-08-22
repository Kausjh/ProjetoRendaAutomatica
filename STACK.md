# STACK

> Fonte oficial e resumida das tecnologias utilizadas pelo Projeto Renda Automática.
>
> Este arquivo registra tanto as versões mínimas aceitas quanto as versões efetivamente validadas no ambiente principal.
>
> Sempre que uma tecnologia for adicionada, removida, atualizada ou validada em outro ambiente, este documento deve ser atualizado juntamente com o `CHANGELOG.md`.

---

## 1. Estado atual do ambiente

| Item | Estado |
|---|---|
| Última validação registrada | 29/07/2026 |
| Sistema operacional | Windows 10 Pro |
| Arquitetura | 64 bits |
| Ambiente virtual | `.venv` |
| Python mínimo declarado | 3.11 |
| Python atualmente validado | 3.13.15 |
| Pip | 26.1.2 |
| Conflitos de dependências | Nenhum |
| Testes automatizados | 95 aprovados |
| Playwright | Funcionando |
| Chromium | Funcionando |
| Ruff | Aprovado |
| Black | Executado |
| isort | Executado |
| MyPy | Estrutura sem duplicação conhecida de módulos |
| Bandit | Executado |
| pip-audit | Executado |
| pre-commit | Executado |

---

## 2. Política de versões

O projeto diferencia três conceitos.

### Versão mínima

É a menor versão declarada como aceita pelo projeto.

Exemplo:

```toml
requires-python = ">=3.11"
```

Isso significa que o código declara exigir Python 3.11 ou superior.

Essa declaração não garante automaticamente que todas as versões futuras do Python serão compatíveis com todas as dependências.

---

### Versão atualmente validada

É a versão utilizada no ambiente real em que:

- as dependências foram instaladas;
- o Playwright foi importado;
- o Chromium foi iniciado;
- os testes foram executados;
- o projeto foi analisado pelas ferramentas de qualidade.

Atualmente:

```text
Python 3.13.15
```

---

### Versão travada

É uma versão que deve ser instalada exatamente como registrada.

Exemplo:

```text
playwright==1.61.0
```

Esse tipo de travamento é utilizado para reduzir diferenças de comportamento entre ambientes.

---

## 3. Python

### Versão mínima declarada

```text
Python 3.11
```

### Versão atualmente validada

```text
Python 3.13.15
```

### Executável validado

```text
C:\Projetos\ProjetoRendaAutomatica\.venv\Scripts\python.exe
```

### Configuração declarada

```toml
[project]
requires-python = ">=3.11"
```

### Configurações de ferramentas

O projeto ainda possui ferramentas configuradas com referência ao Python 3.11:

```toml
[tool.black]
target-version = ["py311"]

[tool.ruff]
target-version = "py311"

[tool.mypy]
python_version = "3.11"
```

Essas configurações indicam que o código deve permanecer compatível com a sintaxe e os recursos considerados válidos para Python 3.11.

Elas não significam que o ambiente virtual esteja executando Python 3.11.

---

## 4. Histórico de compatibilidade do Python

Durante uma instalação anterior do projeto em outro computador, ocorreu um conflito entre uma versão do Python e uma ou mais dependências.

O nome exato da dependência responsável e a versão exata do Python envolvida não foram preservados.

Por esse motivo, o projeto não deve atribuir o incidente a uma biblioteca específica sem evidência.

O fato confirmado é:

> O projeto já apresentou um conflito de compatibilidade durante a reprodução do ambiente em outro computador.

O ambiente atual, entretanto, foi validado com:

```text
Python 3.13.15
```

Nesse ambiente:

- `pip check` não encontrou conflitos;
- o Playwright funcionou;
- o Chromium foi iniciado;
- os testes foram aprovados.

Portanto, Python 3.13.15 é a versão atualmente validada, mas futuras versões do Python não devem ser adotadas sem novo diagnóstico.

---

## 5. Stack principal

| Categoria | Tecnologia | Versão mínima ou declarada | Versão validada |
|---|---|---:|---:|
| Linguagem | Python | 3.11 | 3.13.15 |
| Gerenciador | pip | Não travada | 26.1.2 |
| Automação web | Playwright | Não travada no `requirements.txt` | 1.61.0 |
| Navegador | Chromium | Gerenciado pelo Playwright | Funcionando |
| HTTP | Requests | 2.34.2 | 2.34.2 |
| HTTP assíncrono | HTTPX | 0.28.1 | 0.28.1 |
| Parsing HTML | BeautifulSoup4 | 4.15.0 | 4.15.0 |
| Dados | Pandas | 3.0.3 | 3.0.3 |
| Dados numéricos | NumPy | 2.5.1 | 2.5.1 |
| Telegram | python-telegram-bot | 22.8 | 22.8 |
| Ambiente | python-dotenv | 1.2.2 | 1.2.2 |

---

## 6. Automação web

### Playwright

Versão validada:

```text
1.61.0
```

Finalidades:

- controle de navegador;
- abertura de páginas;
- interação com elementos;
- automação de pesquisas;
- coleta de conteúdo dinâmico;
- conexão via CDP;
- uso de perfis persistentes;
- manutenção de sessões autenticadas.

Status:

```text
Aprovado
```

---

### Chromium

Versão:

```text
Gerenciada pelo Playwright
```

Resultado do diagnóstico:

```text
Chromium OK
```

O navegador foi iniciado em modo headless com sucesso.

---

### CDP

Nome completo:

```text
Chrome DevTools Protocol
```

Finalidade:

- conectar o projeto a um navegador já aberto;
- reutilizar cookies;
- manter autenticações;
- controlar uma sessão persistente;
- reaproveitar um perfil existente.

CDP não é uma dependência instalada separadamente pelo `pip`.

---

## 7. Requisições HTTP

### Requests

Versão:

```text
2.34.2
```

Finalidade:

- requisições HTTP síncronas;
- chamadas diretas a páginas e APIs;
- operações que não exigem navegador.

---

### HTTPX

Versão:

```text
0.28.1
```

Finalidade:

- requisições HTTP modernas;
- suporte síncrono e assíncrono;
- clientes persistentes;
- controle de timeout.

---

### HTTPCore

Versão:

```text
1.0.9
```

Dependência interna do HTTPX.

---

### AnyIO

Versão:

```text
4.14.2
```

Camada de suporte a execução assíncrona.

---

### H11

Versão:

```text
0.16.0
```

Implementação do protocolo HTTP/1.1 utilizada por dependências da stack.

---

## 8. Parsing de HTML

### BeautifulSoup4

Versão:

```text
4.15.0
```

Finalidade:

- interpretar HTML;
- localizar elementos;
- extrair textos;
- extrair links;
- analisar páginas salvas.

---

### SoupSieve

Versão:

```text
2.8.4
```

Responsável pelo suporte a seletores CSS utilizado pelo BeautifulSoup.

---

## 9. Dados

### Pandas

Versão:

```text
3.0.3
```

Finalidade:

- manipulação de tabelas;
- consolidação de produtos;
- análise de dados;
- geração de relatórios;
- comparação de ofertas.

---

### NumPy

Versão:

```text
2.5.1
```

Finalidade:

- operações numéricas;
- cálculos;
- suporte interno ao Pandas;
- pontuação e processamento de dados.

---

## 10. Telegram

### python-telegram-bot

Versão:

```text
22.8
```

Finalidade:

- publicação automática de ofertas;
- envio de mensagens;
- divulgação de links de afiliado;
- integração com canais e bots.

---

## 11. Variáveis de ambiente

### python-dotenv

Versão:

```text
1.2.2
```

Finalidade:

- carregar o arquivo `.env`;
- proteger tokens;
- proteger IDs;
- armazenar configurações locais;
- evitar credenciais dentro do código.

Regra:

```text
O arquivo .env nunca deve ser versionado.
```

---

## 12. Ferramentas de desenvolvimento

| Ferramenta | Versão mínima declarada | Versão validada |
|---|---:|---:|
| pytest | 8.3.0 | 9.1.1 |
| pytest-cov | 6.0.0 | 7.1.0 |
| Ruff | 0.12.0 | 0.16.0 |
| Black | 25.0.0 | 26.5.1 |
| isort | 6.0.0 | 8.0.1 |
| MyPy | 1.16.0 | 2.3.0 |
| Bandit | 1.8.0 | 1.9.4 |
| pip-audit | 2.9.0 | 2.10.1 |
| pre-commit | 4.2.0 | 4.6.1 |

---

## 13. Testes

### pytest

Versão validada:

```text
9.1.1
```

Resultado da última validação:

```text
95 passed
```

Arquivo de configuração:

```text
pyproject.toml
```

Diretório oficial:

```text
tests
```

---

### pytest-cov

Versão validada:

```text
7.1.0
```

Finalidade:

- medir cobertura de testes;
- identificar trechos sem validação;
- apoiar a expansão da suíte de testes.

---

## 14. Qualidade de código

### Ruff

Versão validada:

```text
0.16.0
```

Resultado:

```text
All checks passed!
```

Status:

```text
Aprovado
```

---

### Black

Versão validada:

```text
26.5.1
```

Finalidade:

- padronização automática;
- formatação consistente;
- redução de diferenças de estilo.

---

### isort

Versão validada:

```text
8.0.1
```

Finalidade:

- organização de imports;
- alinhamento com o perfil do Black.

---

### MyPy

Versão validada:

```text
2.3.0
```

Status atual:

```text
Estrutura sem duplicação conhecida de módulos
```

A antiga duplicação estrutural do módulo `automation_web` foi removida.

O projeto mantém uma única implementação em:

```text
automation_web\
```

Isso elimina a ambiguidade de descoberta do módulo que anteriormente impedia a análise estática.

---

## 15. Segurança

### Bandit

Versão validada:

```text
1.9.4
```

Finalidade:

- análise estática de segurança;
- identificação de padrões potencialmente inseguros.

---

### pip-audit

Versão validada:

```text
2.10.1
```

Finalidade:

- auditoria de vulnerabilidades conhecidas;
- análise das dependências instaladas.

---

## 16. Hooks de Git

### pre-commit

Versão validada:

```text
4.6.1
```

Finalidade:

- executar validações antes dos commits;
- impedir arquivos mal formatados;
- verificar sintaxe de arquivos;
- reduzir erros antes do envio ao GitHub.

---

## 17. Dependências auxiliares principais

| Biblioteca | Versão validada |
|---|---:|
| certifi | 2026.6.17 |
| charset-normalizer | 3.4.9 |
| greenlet | 3.5.4 |
| h11 | 0.16.0 |
| httpcore | 1.0.9 |
| idna | 3.18 |
| pyee | 13.0.1 |
| python-dateutil | 2.9.0.post0 |
| six | 1.17.0 |
| soupsieve | 2.8.4 |
| typing_extensions | 4.16.0 |
| tzdata | 2026.3 |
| urllib3 | 2.7.0 |

---

## 18. Build e empacotamento

### setuptools

Versão mínima declarada:

```text
68
```

### wheel

Versão:

```text
Definida pelo ambiente
```

Configuração:

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

---

## 19. Ambiente principal de desenvolvimento

| Item | Definição |
|---|---|
| Sistema operacional | Windows 10 Pro |
| Editor | Visual Studio Code |
| Shell | PowerShell |
| Controle de versão | Git |
| Hospedagem | GitHub |
| Automação remota | GitHub Actions |
| Ambiente virtual | venv |
| Diretório do ambiente | `.venv` |

---

## 20. Arquivos de dependências

### `requirements.txt`

Contém as dependências necessárias para executar a aplicação.

---

### `requirements-dev.txt`

Contém:

- dependências de produção;
- ferramentas de testes;
- ferramentas de qualidade;
- ferramentas de segurança;
- hooks de Git.

---

### `requirements-lock.txt`

Registra as versões exatas do ambiente reproduzível.

O lock atual contém Playwright 1.61.0 e as dependências diretas de produção.

Ele ainda deverá ser revisado para refletir com precisão todo o ambiente de desenvolvimento validado.

---

### `pyproject.toml`

Centraliza configurações de:

- projeto;
- Python;
- Black;
- Ruff;
- isort;
- MyPy;
- pytest;
- coverage;
- build.

---

## 21. Política de atualização

Toda atualização de tecnologia deve seguir esta ordem:

1. Criar um ambiente de teste.
2. Atualizar a dependência.
3. Executar `pip check`.
4. Executar o Playwright.
5. Testar o Chromium.
6. Executar os testes.
7. Executar Ruff.
8. Executar Black.
9. Executar isort.
10. Executar MyPy.
11. Executar Bandit.
12. Executar pip-audit.
13. Executar pre-commit.
14. Testar o pipeline.
15. Testar os scrapers afetados.
16. Atualizar `requirements.txt`.
17. Atualizar `requirements-dev.txt`, quando necessário.
18. Atualizar `requirements-lock.txt`.
19. Atualizar `STACK.md`.
20. Atualizar a documentação detalhada.
21. Atualizar `CHANGELOG.md`.
22. Criar um commit específico.

---

## 22. Política para novas versões do Python

Uma nova versão do Python não deve ser considerada compatível automaticamente.

Antes de adotá-la, será obrigatório validar:

- instalação limpa;
- dependências;
- Playwright;
- Chromium;
- scrapers;
- pipeline;
- Telegram;
- testes;
- ferramentas de qualidade;
- ferramentas de segurança;
- pre-commit;
- CI do GitHub.

A versão atualmente validada é:

```text
Python 3.13.15
```

---

## 23. Comandos de verificação

### Python

```powershell
python --version
```

### Executável ativo

```powershell
python -c "import sys; print(sys.executable)"
```

### Pip

```powershell
python -m pip --version
```

### Dependências quebradas

```powershell
pip check
```

### Dependências instaladas

```powershell
pip list
```

### Testes

```powershell
pytest
```

### Ruff

```powershell
ruff check .
```

### Black

```powershell
black --check .
```

### isort

```powershell
isort --check-only .
```

### MyPy

```powershell
mypy .
```

### Bandit

```powershell
bandit -r . -x .venv,tests
```

### pip-audit

```powershell
pip-audit
```

### pre-commit

```powershell
pre-commit run --all-files
```

---

## 24. Regra obrigatória

A documentação deve refletir o ambiente real.

Nunca registrar como versão oficial uma versão baseada apenas em:

- suposição;
- configuração mínima;
- memória;
- expectativa;
- documentação externa.

Toda versão validada deve ser confirmada por diagnóstico executado dentro do ambiente virtual do projeto.

---

## 25. Histórico de validação

| Data | Python | Testes | Playwright | Dependências | Observação |
|---|---:|---:|---|---|---|
| 29/07/2026 | 3.13.14 | 6 aprovados | Funcionando | Sem conflitos | MyPy falhou por módulo duplicado |

---

# 63.8738, -149.7525
