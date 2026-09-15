# Descoberta Comunitária V1 — Intake autenticado

<!-- 63.8738, -149.7525 -->

## Objetivo

Permitir que um usuário autenticado envie ao Radar o link de uma promoção encontrada por ele, preservando autoria e estado da contribuição sem publicar ou confiar automaticamente no conteúdo recebido.

Esta fase cria o **intake real** da Descoberta Comunitária. O envio já é persistido no banco usado pela identidade do usuário e pode ser consultado novamente pelo próprio autor.

## Rotas

```text
POST /api/v1/me/discoveries
GET  /api/v1/me/discoveries
```

As duas rotas:

- preservam a proteção do token da API quando ele estiver configurado;
- exigem uma sessão de usuário válida;
- isolam contribuições por conta;
- usam o envelope user-facing existente.

### Criar uma contribuição

Payload aceito:

```json
{
  "url": "https://www.kabum.com.br/produto/..."
}
```

`conta_id`, status, identificadores internos e eventual `canonical_key` nunca são aceitos do cliente.

O servidor:

1. valida o formato do link;
2. aceita apenas `http` ou `https`;
3. bloqueia credenciais embutidas e endereços locais/privados explícitos;
4. remove fragmento e normaliza domínio/esquema para deduplicação;
5. identifica o marketplace apenas quando o domínio é conhecido;
6. vincula a contribuição à conta autenticada;
7. persiste o estado inicial `received`.

O mesmo usuário enviando novamente a mesma URL normalizada recebe a contribuição já existente. Usuários diferentes podem contribuir com a mesma oferta, preservando atribuição individual.

## Persistência

A tabela `community_discoveries` fica no mesmo SQLite da identidade pública e possui `FOREIGN KEY` para `contas_usuario`.

Estados reservados:

- `received`;
- `processing`;
- `retry`;
- `approved`;
- `rejected`.

Também são persistidos `tentativas`, `disponivel_em` e `processando_desde`, preparando a fila para o processador da próxima fase sem exigir uma segunda tabela de ingestão.

## Proteções

O intake não realiza requisições externas ao link recebido.

Isso é deliberado: buscar uma URL fornecida por usuário exige nova validação de destino, redirects e resolução DNS no processador para evitar SSRF. A validação de rede será feita antes de qualquer fetch na fase de processamento.

Existe ainda um limite de 30 novas contribuições por conta a cada hora. Reenvio idempotente do mesmo link não consome uma nova contribuição.

## Integração com o pipeline existente

Uma URL isolada **não** deve ser gravada diretamente no Catálogo Canônico.

O Catálogo Canônico exige uma `Oferta` já identificada e normalizada, incluindo identidade canônica confiável, marketplace e identificador do anúncio. Por isso o fluxo correto é:

```text
usuário
  -> community_discoveries (received)
  -> processador de descoberta comunitária
  -> resolução/validação do link
  -> Oferta
  -> validação + normalização existentes
  -> Catálogo Canônico
  -> Price Intelligence
  -> Alert Engine / curadoria / demais etapas existentes
```

A próxima fase liga a fila `received/retry` ao caminho de resolução já usado pelos mecanismos de descoberta, reaproveitando o pipeline em vez de criar uma arquitetura paralela.

## App

A tela pública **Encontrou uma oferta?** permite:

- colar um link;
- enviar para análise;
- acompanhar as contribuições recentes;
- ver o estado informado pelo backend.

O app não afirma que a oferta foi aprovada, publicada ou validada enquanto o backend não mudar seu estado.
