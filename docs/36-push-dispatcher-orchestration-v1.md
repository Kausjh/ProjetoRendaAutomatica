# Push Dispatcher Orchestration V1

## Objetivo

Esta fase liga a Notification Outbox, os dispositivos ativos, o builder de
payload e o Expo Push Gateway em um orquestrador testavel.

Ela ainda nao inicia worker continuo e nao envia push real automaticamente.

## Envio

O fluxo de envio:

1. reserva atomicamente um item pending da outbox;
2. resolve o match e o produto canonico;
3. monta title, body e `data.canonicalKey`;
4. lista somente dispositivos ativos da conta;
5. envia um batch ao Expo Push Service;
6. persiste um ticket por dispositivo;
7. mantem a outbox em processing quando existe ticket aceito.

Ticket `ok` nao marca a outbox como delivered.

## Receipts

A consulta de receipts:

- persiste cada receipt recebido;
- revoga somente o dispositivo relacionado a `DeviceNotRegistered`;
- marca a outbox como delivered quando ao menos um receipt e `ok`;
- mantem processing enquanto algum receipt da tentativa atual esta ausente;
- aplica retry a erros temporarios conhecidos;
- finaliza como failed quando a tentativa atual terminou sem entrega e sem
  erro temporario.

## Multiplos dispositivos

Uma falha terminal em um aparelho nao derruba a notificacao inteira quando
outro dispositivo possui ticket/receipt valido.

## Idempotencia e tentativas

Cada tentativa persistida registra o numero `tentativas` da outbox no momento
do envio. Isso permite distinguir batches de retries posteriores.

Um receipt `ok` de qualquer tentativa conhecida comprova que pelo menos um
provider recebeu a notificacao e encerra a outbox como delivered.

## Seguranca

Push tokens continuam restritos ao cadastro interno de dispositivos. A tabela
de delivery nao persiste o token.

## Fronteiras

Esta fase nao:

- cria rota HTTP;
- adiciona worker continuo;
- liga o dispatcher ao `main.py`;
- envia push real nos testes;
- executa smoke test no aparelho.

A proxima fase adiciona o worker controlado e, somente depois dos testes, o
primeiro envio real de ponta a ponta.
