# Instalação

> Este documento descreve como instalar, configurar e executar o Projeto Renda Automática em uma máquina nova.

---

# Requisitos

Antes de iniciar, certifique-se de possuir:

- Python 3.12 ou superior
- Git
- Google Chrome instalado
- Visual Studio Code (recomendado)
- Conta no Telegram
- Credenciais dos programas de afiliados utilizados

---

# Clonando o Projeto

Clone o repositório:

```bash
git clone <URL_DO_REPOSITORIO>
```

Entre na pasta:

```bash
cd ProjetoRendaAutomatica
```

---

# Criando o Ambiente Virtual

Windows:

```bash
python -m venv .venv
```

Ative:

```bash
.venv\Scripts\activate
```

Linux:

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

# Instalando Dependências

```bash
pip install -r requirements.txt
```

---

# Instalando os Navegadores do Playwright

Caso o projeto utilize Playwright:

```bash
playwright install
```

ou

```bash
python -m playwright install
```

---

# Configurando o Projeto

Crie o arquivo:

```
.env
```

Utilize o arquivo:

```
.env.example
```

como referência.

Nunca envie o `.env` para o GitHub.

---

# Estrutura Esperada

Após configurar, a estrutura deve ficar semelhante a:

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

├── .env
├── launcher.py
├── main.py
└── requirements.txt
```

---

# Configuração do Telegram

Verifique se:

- Token do Bot está correto.
- Canal existe.
- Bot é administrador.
- Permissões de envio estão habilitadas.

Sem isso nenhuma publicação será realizada.

---

# Configuração dos Afiliados

Configure as credenciais necessárias.

Exemplos:

- Mercado Livre
- Amazon
- Shopee

Cada integração pode possuir requisitos específicos.

---

# Chrome

O projeto utiliza uma sessão real do Chrome.

Certifique-se de que:

- o Chrome esteja instalado;
- o perfil utilizado esteja acessível;
- nenhuma configuração impeça sua inicialização.

---

# Executando

Método recomendado:

```bash
python launcher.py
```

ou

```bash
python main.py
```

dependendo da configuração atual do projeto.

---

# Fluxo Esperado

Ao iniciar corretamente, o sistema executará aproximadamente esta sequência:

```
Inicialização

↓

Carregamento das Configurações

↓

Inicialização dos Afiliadores

↓

Inicialização dos Repositórios

↓

Inicialização dos Serviços

↓

Execução do Pipeline

↓

Coleta das Ofertas

↓

Processamento

↓

Publicação
```

---

# Verificando se Tudo Está Funcionando

Uma execução saudável deve apresentar:

- Inicialização sem erros.
- Scrapers carregados.
- Pipeline iniciado.
- Ofertas coletadas.
- Ofertas processadas.
- Links afiliados gerados.
- Mensagens publicadas.

---

# Problemas Comuns

## Erro de dependências

Execute novamente:

```bash
pip install -r requirements.txt
```

---

## Chrome não inicia

Verifique:

- instalação do Chrome;
- perfil utilizado;
- permissões.

---

## Telegram não publica

Verifique:

- token;
- canal;
- permissões do bot.

---

## Afiliador não gera links

Verifique:

- credenciais;
- cookies;
- configurações;
- marketplace suportado.

---

# Atualizando o Projeto

```bash
git pull
```

Depois:

```bash
pip install -r requirements.txt
```

Caso novas dependências tenham sido adicionadas.

---

# Atualizando o Playwright

Quando necessário:

```bash
playwright install
```

---

# Ambiente Recomendado

- Windows 10 ou superior
- Python atualizado
- Ambiente virtual (.venv)
- Google Chrome atualizado
- Visual Studio Code

---

# Checklist

Antes da primeira execução confirme:

- [ ] Python instalado
- [ ] Git instalado
- [ ] Dependências instaladas
- [ ] Playwright instalado
- [ ] Chrome instalado
- [ ] `.env` configurado
- [ ] Bot do Telegram configurado
- [ ] Programa de afiliados configurado
- [ ] Projeto clonado
- [ ] Ambiente virtual ativo

---

# Conclusão

Após concluir todas as etapas acima, o Projeto Renda Automática estará pronto para executar seu pipeline completo de coleta, processamento, monetização e publicação de ofertas.
