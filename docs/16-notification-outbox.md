# Bloco 30 — Personalized Notification Outbox V1

## Classificação

O preflight do Bloco 30 confirmou duas evidências complementares:

1. o roadmap público lista notificações push depois de contas, preferências e
   watchlists;
2. o Bloco 29 termina deliberadamente sem delivery e documenta como próximo
   estágio uma fila/outbox de entrega.

Por isso o Bloco 30 implementa a fundação persistente de entrega, sem antecipar
um provedor de push ou o aplicativo público.

## Objetivo

Transformar correspondências persistidas do Personalized Alert Matching V1 em
intenções de entrega idempotentes.

A outbox cria a fronteira entre:

`decisão de interesse do usuário -> tentativa futura de entrega`

O matching continua responsável por decidir "quem deve receber". A outbox
passa a ser responsável por manter "o que precisa ser entregue" e seu estado.

## Canal V1

O canal pretendido é:

`push`

Isso significa que os itens ficam preparados para um futuro dispatcher de
push. Este bloco não envia push real.

Não existem neste estágio:

- credenciais de Firebase, APNs ou outro provedor;
- tokens de aparelho;
- chamadas de rede para provedor de push;
- registro público de dispositivos.

## Persistência

A tabela `personalized_notification_outbox` usa o mesmo banco lógico:

`database/user_identity.sqlite3`

Cada combinação:

`match_id + canal`

é única.

Reprocessar a sincronização não duplica itens.

## Estados

A máquina de estados V1 usa:

- `pending`;
- `processing`;
- `delivered`;
- `failed`.

Um item nasce em `pending`.

A reserva muda atomicamente o item elegível para `processing` e incrementa o
contador de tentativas.

A partir de `processing`, o consumidor futuro poderá registrar:

- sucesso -> `delivered`;
- falha recuperável -> volta para `pending` com nova disponibilidade;
- falha terminal -> `failed`.

## Retry

Falhas recuperáveis registram:

- erro normalizado;
- nova data de disponibilidade;
- tentativa já contabilizada na reserva.

Itens agendados para o futuro não podem ser reservados antes da hora.

## Fronteiras

Este bloco não:

- cria novas rotas HTTP;
- envia push de verdade;
- envia email;
- publica no Telegram;
- armazena credenciais de provedor;
- armazena tokens de dispositivo;
- transforma a API administrativa em API de notificações;
- inclui o aplicativo Android privado no repositório público.

A Application API V1 continua read-only.

## Próximos consumidores

A fundação permite implementar posteriormente:

- dispatcher real de push;
- registro de dispositivos do app público;
- feed personalizado;
- interface web;
- extensão de navegador.

Esses consumidores podem evoluir sem reexecutar a lógica de matching do
Bloco 29.

## Critérios de aceite

1. matches persistidos podem ser materializados em outbox;
2. sincronização é idempotente;
3. um item é único por match + canal;
4. reserva incrementa tentativas e muda para `processing`;
5. sucesso termina em `delivered`;
6. retry retorna para `pending` com disponibilidade futura;
7. falha terminal termina em `failed`;
8. item futuro não é reservado prematuramente;
9. nenhuma chamada de rede externa é feita;
10. nenhuma nova rota HTTP é criada;
11. Application API V1 continua read-only.
