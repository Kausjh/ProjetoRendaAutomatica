# Radar de Ofertas

> Sistema automatizado para descoberta, acompanhamento, análise, curadoria e publicação de ofertas de hardware, periféricos, eletrônicos e produtos de setup.

O **Radar de Ofertas** monitora produtos em marketplaces, mantém um histórico próprio de preços e transforma dados brutos em ofertas selecionadas para publicação.

O projeto nasceu como uma automação de afiliados e evoluiu para uma arquitetura modular que separa **coleta, identidade de produtos, histórico, classificação, pontuação, curadoria, fila editorial, monetização, publicação e consulta**.

## O que o sistema faz hoje

- coleta produtos automaticamente no Mercado Livre;
- acompanha preços ao longo do tempo;
- normaliza e classifica produtos;
- identifica anúncios e famílias de produtos para reduzir duplicações;
- calcula pontuação para priorizar oportunidades;
- detecta anomalias e quedas suspeitas de preço;
- aplica regras de curadoria antes da publicação;
- mantém uma fila inteligente com diversidade por categoria;
- evita republicações excessivas de produtos semelhantes;
- publica em cadência variável, evitando rajadas artificiais;
- transforma URLs elegíveis em links de afiliado;
- oferece um bot de consulta com histórico, menor preço e categorias;
- executa continuamente com recuperação automática após falhas de rede;
- controla processos concorrentes e recupera travas órfãs.

## Fluxo principal

```text
Marketplace
    │
    ▼
Scraper
    │
    ▼
Normalização e identidade
    │
    ▼
Histórico de preços
    │
    ▼
Classificação e pontuação
    │
    ▼
Detecção de anomalias
    │
    ▼
Curadoria editorial
    │
    ▼
Deduplicação por família
    │
    ▼
Fila inteligente
    │
    ▼
Monetização / afiliados
    │
    ▼
Formatação
    │
    ▼
Publicação no Telegram
```

Paralelamente, o histórico alimenta o **bot de consulta**, permitindo pesquisar produtos e comparar o preço atual com os registros já coletados.

## Recursos

### Histórico próprio de preços

Cada produto acompanhado pode acumular verificações ao longo do tempo. Isso permite apresentar informações como:

- preço atual;
- menor preço registrado;
- maior preço registrado;
- média histórica;
- quantidade de verificações;
- período acompanhado.

O sistema deixa explícito quando o histórico ainda é curto, evitando apresentar o menor preço observado como se fosse necessariamente o menor preço de toda a existência do produto.

### Curadoria e Score

Nem tudo que é coletado vira publicação.

As ofertas passam por classificação, pontuação e regras editoriais antes de entrarem na fila. O objetivo é priorizar oportunidades mais interessantes e reduzir produtos irrelevantes, preços pouco competitivos e conteúdo repetitivo.

### Identidade e deduplicação

Anúncios diferentes podem representar essencialmente o mesmo produto.

O projeto utiliza normalização e identificação de famílias para reduzir publicações praticamente duplicadas e aplicar cooldown entre itens equivalentes, preservando a possibilidade de republicação quando ocorre uma queda de preço relevante.

### Fila editorial e cadência

A publicação é desacoplada da coleta.

Ofertas aprovadas entram em uma fila persistente e são publicadas por um processo próprio. A seleção considera prioridade e diversidade, enquanto a cadência utiliza intervalos variáveis em vez de despejar várias mensagens de uma vez.

### Detecção de anomalias

Quedas muito grandes de preço recebem tratamento especial.

O sistema pode colocar ofertas suspeitas em revisão ou impedir automaticamente a publicação de valores com forte indício de erro, reduzindo o risco de divulgar preços incorretos.

### Bot de consulta

O bot permite consultar a base acumulada diretamente pelo Telegram.

Exemplos:

```text
ryzen 7 5700x
/menorpreco ryzen 7 5700x
/historico ryzen 7 5700x
/categoria monitor
/categorias
```

Também é possível fazer uma comparação de preços:

```text
rtx 4060 vs rx 7600
```

A comparação utiliza **preço e histórico monitorado**. Ela não pretende substituir uma comparação técnica de desempenho entre os produtos.

### Runtime resiliente

O projeto possui um runtime responsável por manter os componentes principais em execução.

Entre os mecanismos implementados estão:

- prevenção de execuções concorrentes;
- detecção e remoção de locks órfãos;
- monitoramento de conectividade;
- suspensão controlada durante indisponibilidade de rede;
- encerramento da árvore de processos no Windows;
- reinicialização automática dos serviços;
- retomada do pipeline após recuperação da conexão.

## Arquitetura

A organização privilegia separação de responsabilidades:

```text
ProjetoRendaAutomatica/
├── affiliates/          # geração e integração de links afiliados
├── automation_web/      # automação e navegador persistente
├── bots/                # integração de publicação
├── config/              # configuração da aplicação
├── database/            # dados persistidos localmente
├── docs/                # documentação técnica
├── filters/             # filtros do domínio
├── formatters/          # apresentação das ofertas
├── models/              # entidades do domínio
├── repositories/        # persistência e acesso a dados
├── scrapers/            # coleta em marketplaces
├── scripts/             # utilitários operacionais
├── services/            # regras de negócio e orquestração
├── tests/               # testes automatizados
├── bot_consulta.py      # interface de consulta
├── publicador_fila.py   # consumidor da fila editorial
├── runtime.py           # ponto de entrada do runtime contínuo
└── main.py              # pipeline de coleta e processamento
```

A entidade central continua sendo `Oferta`, enriquecida progressivamente durante o processamento.

## Componentes principais

| Componente | Responsabilidade |
|---|---|
| Scraper | Descobrir e coletar produtos |
| Normalizador | Padronizar identidade e características |
| Histórico | Registrar evolução dos preços |
| Classificador | Determinar categoria e atributos |
| Pontuador | Estimar relevância da oportunidade |
| Detector de anomalias | Segurar preços potencialmente incorretos |
| Curadoria | Decidir o que merece seguir para publicação |
| Identificador de família | Reduzir duplicações entre anúncios equivalentes |
| Fila de publicação | Desacoplar descoberta e distribuição |
| Seletor editorial | Priorizar e diversificar a saída |
| Afiliadores | Transformar URLs quando houver integração disponível |
| Publicador | Distribuir ofertas no canal |
| Bot de consulta | Consultar histórico e preços |
| Runtime | Supervisionar os processos e a recuperação operacional |

## Qualidade

A suíte automatizada possui atualmente **95 testes** cobrindo componentes como:

- consulta e busca de produtos;
- classificação e identidade;
- pontuação;
- curadoria;
- deduplicação;
- diversidade da fila;
- cadência de publicação;
- persistência da fila;
- locks de execução;
- resiliência de rede;
- recuperação do runtime;
- encerramento de árvores de processos.

Execute:

```bash
python -m pytest
```

Ferramentas de qualidade utilizadas pelo projeto incluem **Black**, **Ruff**, **MyPy** e **pre-commit**.

## Tecnologias

- Python 3.11+
- Playwright
- Requests
- python-telegram-bot
- SQLite
- JSON
- Pytest
- Black
- Ruff
- MyPy
- Git / GitHub

## Instalação

O guia completo está em:

```text
docs/07-instalacao.md
```

Em linhas gerais:

```bash
git clone <URL_DO_REPOSITORIO>
cd ProjetoRendaAutomatica

python -m venv .venv
```

No Windows:

```powershell
.venv\Scripts\activate
```

Instale as dependências conforme a configuração atual do projeto, prepare o Playwright e crie seu `.env` a partir de `.env.example`.

Credenciais reais, tokens, cookies e perfis de navegador **não devem ser versionados**.

## Configuração

As configurações públicas e valores de exemplo ficam no repositório. Segredos devem permanecer exclusivamente no ambiente local.

Exemplo:

```text
.env.example  → modelo público
.env          → configuração local e privada
```

Nunca publique o conteúdo real do `.env`.

## Documentação

A documentação técnica fica em `docs/` e cobre instalação, arquitetura, decisões técnicas e stack utilizada.

O arquivo `STACK.md` mantém uma visão consolidada do ambiente e das decisões de infraestrutura do projeto.

## Estado atual

O projeto está em desenvolvimento ativo.

O foco atual é consolidar a qualidade da seleção de ofertas, ampliar a cobertura de produtos e evoluir a automação sem transformar o sistema em uma sequência indiscriminada de publicações.

## Roadmap

Evoluções planejadas incluem:

- ampliar a cobertura de marketplaces;
- aprimorar a qualidade da identificação de produtos;
- aumentar a profundidade do histórico de preços;
- evoluir ranking e curadoria;
- melhorar observabilidade e métricas;
- criar ferramentas de administração e acompanhamento;
- explorar novos canais de distribuição;
- avaliar uma API e interface web quando houver necessidade real.

O roadmap é evolutivo: novas tecnologias só devem entrar quando resolverem um problema concreto do sistema.

## Segurança

O repositório utiliza `.gitignore` para impedir o versionamento de arquivos locais e sensíveis, incluindo variáveis de ambiente, credenciais, perfis de navegador, bancos de runtime e arquivos auxiliares do SQLite.

Se uma credencial for publicada por engano, removê-la em um commit posterior **não é suficiente**: ela deve ser revogada e o histórico deve ser tratado adequadamente.

## Licença

Este projeto é distribuído sob a licença MIT.

---

**Radar de Ofertas** — automação orientada por dados para monitoramento, seleção e distribuição de oportunidades comerciais.
