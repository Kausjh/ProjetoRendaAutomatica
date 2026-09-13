# Bloco 28 — User Personalization & Watchlists V1

## Objetivo

Adicionar a primeira camada persistente de personalização por usuário sobre a
fundação de identidade do Bloco 27.

O roadmap da plataforma pública lista preferências e watchlists logo depois
de contas de usuários. Este bloco implementa essas duas capacidades sem
expor uma nova superfície HTTP.

## Preferências V1

Cada conta ativa pode manter:

- notificações de preço habilitadas ou desabilitadas;
- lista normalizada de marketplaces preferidos.

A ausência de marketplaces preferidos significa que a preferência não
restringe a origem por marketplace.

## Watchlists V1

Cada conta ativa pode acompanhar produtos pelo `canonical_key`.

Um item pode possuir:

- preço alvo opcional;
- flag para futura notificação de queda de preço.

O preço alvo é persistido em centavos inteiros para evitar dependência de
ponto flutuante na persistência.

Existe no máximo um item por combinação:

`conta_id + canonical_key`

Adicionar novamente o mesmo produto atualiza sua configuração, preservando a
identidade original do item.

## Integração com identidade

A camada exige uma conta existente e ativa do User Identity V1.

As tabelas usam o mesmo banco lógico de identidade:

`database/user_identity.sqlite3`

Assim, preferências e watchlists podem utilizar integridade referencial sem
transformar a identidade em uma API pública.

## Fronteiras

Este bloco:

- não cria rotas HTTP;
- não altera o contrato read-only da Application API V1;
- não dispara Alert Engine;
- não envia push;
- não publica no Telegram;
- não usa o Bearer de infraestrutura como identidade de usuário;
- não transforma a API administrativa em API de personalização;
- não inclui o aplicativo Android privado no repositório público.

A futura camada de alertas personalizados poderá consumir as watchlists e
preferências sem acoplar o domínio de usuário ao control plane.

## Critérios de aceite

1. somente contas existentes e ativas podem usar personalização;
2. preferências possuem defaults seguros;
3. marketplaces são normalizados e deduplicados;
4. watchlist é isolada por conta;
5. um produto é único por conta + `canonical_key`;
6. preço alvo é opcional, positivo e persistido em centavos;
7. atualização preserva a identidade do item;
8. remoção afeta somente o usuário dono do item;
9. nenhuma nova rota HTTP é criada;
10. Alert Engine continua sem entrega personalizada neste bloco;
11. Application API V1 continua read-only.
