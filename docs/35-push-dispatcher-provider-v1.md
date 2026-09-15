# Push Dispatcher Provider V1

## Objetivo

Esta fase adiciona a fundacao de transporte do Push Dispatcher usando o
Expo Push Service e a persistencia de tickets/receipts por dispositivo.

Ela ainda nao consome automaticamente a outbox, nao revoga dispositivos e
nao envia push real.

## Expo Push Service

O gateway usa:

- `https://exp.host/--/api/v2/push/send`
- `https://exp.host/--/api/v2/push/getReceipts`

Os limites aplicados localmente sao:

- no maximo 100 mensagens por request de envio;
- no maximo 1000 receipt IDs por request de consulta.

## Semantica de entrega

Um push ticket com `status=ok` significa apenas que o Expo Push Service
aceitou a mensagem e forneceu um receipt ID.

Um push receipt com `status=ok` significa que FCM ou APNs aceitou a
notificacao. Isso ainda nao prova apresentacao ou leitura no aparelho.

Por isso, esta fase nao usa ticket `ok` como sinonimo de `delivered` na
outbox.

## Persistencia

A tabela `push_delivery_attempts` registra por tentativa:

- outbox;
- dispositivo;
- Expo receipt/ticket ID;
- status do ticket;
- status do receipt;
- codigo de erro do provedor;
- erro sanitizado;
- timestamps.

O push token nao e persistido nessa tabela.

## Seguranca

Mensagens de erro vindas do provedor sao sanitizadas antes de retornarem
ao dominio, removendo Expo push tokens eventualmente ecoados pelo
provedor.

Os testes usam `httpx.MockTransport` e nao realizam chamadas externas.

## Fronteiras desta fase

Esta fase nao:

- cria novas rotas HTTP;
- inicia worker continuo;
- muda status da Notification Outbox;
- revoga dispositivo em `DeviceNotRegistered`;
- envia push real para o aparelho.

A orquestracao entre Outbox, dispositivos, payload, tickets, receipts,
retry e revogacao pertence a proxima fase.
