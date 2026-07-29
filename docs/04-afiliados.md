# Arquitetura de Afiliados

> Este documento descreve a arquitetura responsável pela monetização do Projeto Renda Automática.

---

# Objetivo

O sistema de afiliados tem uma única responsabilidade:

> Transformar links comuns em links monetizados.

Todo o restante da aplicação trabalha apenas com ofertas.

Somente esta camada conhece detalhes dos programas de afiliados.

---

# Filosofia

O Projeto Renda Automática foi desenvolvido para suportar múltiplos marketplaces.

Por esse motivo, nenhum módulo do sistema deve possuir código semelhante a:

```python
if marketplace == "Mercado Livre":
    ...

elif marketplace == "Amazon":
    ...
```

Esse tipo de decisão pertence exclusivamente à arquitetura de afiliados.

---

# Visão Geral

```
Oferta

↓

GeradorLinkAfiliado

↓

RegistroAfiliadores

↓

Afiliador Compatível

↓

Link Monetizado

↓

Oferta Atualizada
```

---

# Estrutura

```
affiliates/

├── base_afiliador.py
├── gerador_link_afiliado.py
├── registro_afiliadores.py
├── carregador_afiliadores.py
└── ...
```

Cada arquivo possui uma responsabilidade específica.

---

# BaseAfiliador

Responsabilidade:

Definir o contrato que todos os afiliadores devem seguir.

Todo afiliador deve ser capaz de responder duas perguntas:

- Este link pertence a mim?
- Como gerar o link monetizado?

Nenhum outro comportamento é obrigatório.

---

# Afiliadores

Cada marketplace possui sua própria implementação.

Exemplo:

```
Mercado Livre

↓

MercadoLivreAfiliador
```

No futuro poderão existir:

```
AmazonAfiliador

ShopeeAfiliador

KabumAfiliador

TerabyteAfiliador

MagazineLuizaAfiliador
```

Cada um conhece apenas sua própria plataforma.

---

# Registro de Afiliadores

Responsável por manter todos os afiliadores disponíveis na aplicação.

O restante do sistema não precisa conhecer implementações específicas.

Ele apenas solicita um gerador de links.

---

# Carregador de Afiliadores

Responsável por montar o registro da aplicação.

Sua função é inicializar os afiliadores configurados e disponibilizá-los para o sistema.

Isso permite habilitar ou desabilitar marketplaces sem alterar a lógica principal.

---

# Gerador de Links

O Gerador de Links é a porta de entrada da camada comercial.

Fluxo:

```
Oferta

↓

URL Original

↓

Encontrar afiliador compatível

↓

Gerar URL monetizada

↓

Atualizar Oferta
```

Ele nunca sabe qual marketplace está sendo utilizado.

Seu único compromisso é encontrar alguém capaz de gerar o link.

---

# Responsabilidades

| Componente | Responsabilidade |
|------------|------------------|
| BaseAfiliador | Definir o contrato |
| Afiliador | Implementar um marketplace |
| Registro | Armazenar afiliadores |
| Carregador | Inicializar afiliadores |
| Gerador | Encontrar o afiliador correto |

---

# Fluxo de Execução

```
Oferta

↓

GeradorLinkAfiliado

↓

Registro

↓

Lista de Afiliadores

↓

Afiliador 1

↓

Suporta?

↓

Não

↓

Afiliador 2

↓

Suporta?

↓

Sim

↓

Gerar Link

↓

Oferta.link_afiliado
```

Caso nenhum afiliador suporte a URL, o sistema continua utilizando o link original.

---

# Princípios

A camada de afiliados segue os seguintes princípios:

- Baixo acoplamento;
- Alta coesão;
- Arquitetura extensível;
- Implementações independentes;
- Interface comum para todos os marketplaces.

---

# Como adicionar um novo marketplace

Para integrar um novo programa de afiliados, o processo deve seguir esta sequência:

1. Criar uma nova classe que implemente `BaseAfiliador`.
2. Implementar o método responsável por verificar se o link pertence ao marketplace.
3. Implementar a geração do link monetizado.
4. Registrar o afiliador no sistema.
5. Configurar o marketplace conforme necessário.

Nenhuma alteração deve ser realizada no restante da aplicação.

---

# Vantagens da Arquitetura

Esta abordagem permite:

- adicionar marketplaces sem alterar o núcleo do sistema;
- remover marketplaces sem afetar outras integrações;
- testar cada afiliador isoladamente;
- reutilizar a mesma infraestrutura para qualquer programa de afiliados.

---

# Futuras Integrações

A arquitetura foi planejada para suportar facilmente novos parceiros comerciais, como:

- Amazon;
- Shopee;
- Kabum;
- Terabyte;
- Pichau;
- Magazine Luiza;
- AliExpress;
- qualquer outro marketplace que ofereça programa de afiliados.

---

# Conclusão

A camada de afiliados isola completamente a lógica de monetização do restante da aplicação.

Graças a essa separação, o pipeline continua responsável apenas por transformar oportunidades comerciais, enquanto a monetização permanece encapsulada em uma arquitetura modular, extensível e independente.
