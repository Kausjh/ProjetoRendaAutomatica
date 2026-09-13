# Bloco 29 — Personalized Alert Matching V1

## Objetivo

Conectar a semântica dos eventos do Alert Engine às preferências e watchlists
de usuários sem introduzir entrega de notificações.

O resultado deste bloco é uma correspondência persistente entre:

`evento do Alert Engine + item de watchlist + conta`

Essa correspondência é uma intenção de notificação futura, não uma entrega.

## Eventos suportados

V1 reconhece:

- `mudanca_preco`;
- `novo_menor_preco_historico`.

O serviço recebe uma representação normalizada do evento contendo identidade,
`canonical_key`, preço atual, tipo, instante, marketplace opcional e preço
anterior opcional.

## Regras de matching

Um evento somente considera watchlists com o mesmo `canonical_key`.

A preferência `notificacoes_preco_habilitadas=False` bloqueia o match.

Quando existem marketplaces preferidos, o evento precisa possuir marketplace
conhecido e compatível. A ausência dessa evidência falha fechada.

### Preço alvo

Se o item possui preço alvo e o preço atual é menor ou igual ao alvo, o match
recebe:

`target_price_reached`

### Queda de preço

Para `mudanca_preco`, uma queda só é reconhecida quando o preço anterior é
conhecido e o preço atual é menor.

Isso evita tratar qualquer mudança de preço como queda.

O motivo é:

`price_drop_detected`

### Novo menor preço histórico

O evento `novo_menor_preco_historico` já carrega evidência suficiente de queda
relevante para a regra de watchlist:

`new_historical_low`

## Deduplicação

Existe no máximo uma correspondência por:

`evento_alerta_id + watchlist_id`

Reprocessar o mesmo evento é idempotente na persistência.

## Persistência

As correspondências usam o mesmo banco lógico da identidade e personalização:

`database/user_identity.sqlite3`

O preço observado é persistido em centavos inteiros.

## Fronteiras

Este bloco não:

- cria novas rotas HTTP;
- envia push;
- envia email;
- publica no Telegram;
- classifica um evento como "good deal";
- concede autoridade comercial ao Alert Engine;
- altera o contrato read-only da Application API V1;
- transforma a API administrativa em API de alertas personalizados.

O próximo estágio pode consumir as correspondências persistidas e implementar
uma fila/outbox de entrega sem precisar recalcular a intenção de cada usuário.

## Critérios de aceite

1. watchlists são selecionadas por `canonical_key`;
2. preferências de notificação são respeitadas;
3. marketplaces preferidos são respeitados;
4. preço alvo produz match somente quando atingido;
5. mudança de preço exige evidência direcional para ser tratada como queda;
6. novo menor histórico produz motivo próprio;
7. reprocessamento não duplica correspondências;
8. não existe entrega de notificação;
9. nenhuma nova rota HTTP é criada;
10. Application API V1 continua read-only.
