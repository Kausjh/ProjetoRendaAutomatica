# Sistema de Afiliados

> Este documento descreve a arquitetura, o funcionamento e as responsabilidades do sistema de afiliados do Projeto Renda Automática.

---

# Objetivo

O sistema de afiliados é responsável por transformar links comuns em links monetizados, permitindo que toda publicação realizada pelo sistema possa gerar receita.

A monetização deve ocorrer de forma transparente para o restante da aplicação.

Nenhuma outra camada deve conhecer a implementação específica de cada programa de afiliados.

---

# Objetivos Arquiteturais

O sistema foi projetado para permitir:

- adicionar novos programas de afiliados;
- remover programas existentes;
- alterar regras de monetização;
- utilizar diferentes plataformas simultaneamente;
- selecionar automaticamente o afiliador correto.

Todo o restante do sistema deve continuar funcionando independentemente dessas alterações.

---

# Fluxo Geral

```text
Oferta
    │
    ▼
Link Original
    │
    ▼
Gerenciador de Afiliados
    │
    ▼
Seleção do Afiliador
    │
    ▼
Geração do Link
    │
    ▼
Validação
    │
    ▼
Oferta Atualizada
```

Apenas o link da oferta é alterado.

As demais informações permanecem inalteradas.

---

# Estrutura

```text
affiliates/
│
├── base_affiliate.py
├── registry.py
├── manager.py
│
├── amazon.py
├── mercado_livre.py
├── shopee.py
├── kabum.py
└── ...
```

Cada afiliador deve ser implementado de forma independente.

---

# BaseAffiliate

Todos os afiliadores devem herdar da classe base.

A interface mínima esperada é:

```python
class BaseAffiliate:

    def supports(self, oferta) -> bool:
        ...

    def generate_link(self, oferta) -> str:
        ...
```

Essa interface garante que todos os afiliadores possam ser utilizados pelo gerenciador sem tratamento especial.

---

# Responsabilidades

Cada afiliador deve:

- verificar se suporta determinada oferta;
- gerar o link monetizado;
- retornar o link final.

Nada além disso.

---

# O que um afiliador NÃO deve fazer

Um afiliador nunca deve:

- publicar mensagens;
- acessar Telegram;
- salvar arquivos;
- consultar banco de dados;
- executar scraping;
- aplicar filtros;
- calcular pontuação.

Toda lógica de monetização deve limitar-se à geração do link.

---

# Registro de Afiliadores

Todos os afiliadores disponíveis devem ser registrados em um único local.

Exemplo:

```text
Registry

│

├── Amazon

├── Mercado Livre

├── Shopee

├── Kabum

└── Futuros afiliadores
```

O restante da aplicação nunca deve instanciar afiliadores diretamente.

---

# Seleção Automática

O sistema deve escolher automaticamente qual afiliador utilizar.

Fluxo:

```text
Oferta

↓

Registry

↓

supports()

↓

Afiliador Compatível

↓

generate_link()

↓

Link Final
```

Caso nenhum afiliador seja compatível, o link original permanece.

---

# Prioridade

Quando dois afiliadores forem compatíveis com a mesma oferta, a prioridade deverá ser definida pelo Registry.

Exemplo:

```text
Amazon

↓

Mercado Livre

↓

Kabum

↓

Shopee
```

A ordem deve permanecer centralizada.

---

# Regras de Implementação

Cada afiliador deve possuir apenas uma responsabilidade:

Transformar um link comum em um link monetizado.

Nenhuma regra comercial deve existir dentro do afiliador.

---

# Dados Produzidos

Após a monetização, a Oferta poderá conter informações adicionais como:

- link afiliado;
- afiliador utilizado;
- plataforma;
- identificador da campanha;
- parâmetros adicionados ao link.

Esses dados passam a fazer parte do domínio da Oferta.

---

# Tratamento de Falhas

Caso ocorra erro durante a geração do link:

- o pipeline não deve ser interrompido;
- o erro deve ser registrado;
- o link original poderá ser utilizado como fallback.

Essa estratégia garante que a publicação continue acontecendo mesmo quando um programa de afiliados estiver indisponível.

---

# Escalabilidade

A arquitetura suporta qualquer quantidade de afiliadores.

Exemplo:

```text
Amazon

Mercado Livre

Shopee

Kabum

AliExpress

Magazine Luiza

Casas Bahia

Terabyte

Pichau

...
```

Nenhuma alteração estrutural deverá ser necessária.

---

# Fluxo Completo

```text
Oferta

↓

Link Original

↓

Registry

↓

supports()

↓

Afiliador

↓

generate_link()

↓

Validação

↓

Oferta Atualizada
```

---

# Boas Práticas

Cada afiliador deve:

- implementar apenas sua própria plataforma;
- possuir testes independentes;
- não depender de outros afiliadores;
- respeitar a interface BaseAffiliate;
- ser facilmente removível.

---

# Evolução Prevista

O sistema poderá futuramente oferecer:

- múltiplos links para a mesma oferta;
- comparação automática entre afiliadores;
- seleção baseada em comissão;
- seleção baseada em conversão histórica;
- campanhas promocionais;
- parâmetros dinâmicos;
- A/B Testing;
- estatísticas por plataforma;
- balanceamento entre afiliadores.

A arquitetura atual já suporta essa evolução sem necessidade de alterações significativas.

---

# Resumo

O sistema de afiliados é completamente desacoplado do restante da aplicação.

Sua única responsabilidade é transformar links comuns em links monetizados, permitindo que novos programas de afiliados sejam adicionados com o menor impacto possível no restante da arquitetura.
