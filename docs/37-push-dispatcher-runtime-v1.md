# Push Dispatcher Runtime V1

## Objetivo

A Fase 3B conecta a orquestracao do Push Dispatcher ao Runtime Unificado sem
habilitar envio real automaticamente.

O Push Dispatcher roda como processo filho separado, supervisionado pelo mesmo
`OrquestradorRuntime` que ja gerencia bot, publicador e pipeline.

## Fail-closed

A variavel `RUNTIME_PUSH_DISPATCHER_ATIVO` usa `false` como padrao.

Enquanto ela permanecer falsa:

- o processo do Push Dispatcher nao e iniciado;
- a Expo Push Service nao e chamada pelo runtime;
- nenhum push real e enviado.

A Fase 3B nao altera o `.env` local.

## Ciclo

Quando ativado futuramente, o worker:

1. consulta receipts que ja atingiram a idade minima;
2. reserva itens disponiveis da outbox;
3. resolve payload e dispositivos ativos;
4. envia via Expo Push Service;
5. persiste tickets por dispositivo;
6. aguarda receipts antes de concluir `delivered`;
7. respeita retry e `DeviceNotRegistered`.

O burst por ciclo e limitado para impedir uma drenagem agressiva da outbox.

## Receipts

`RUNTIME_PUSH_RECEIPT_MIN_AGE_SEGUNDOS` usa `900` por padrao.

Isso mantem o runtime alinhado a recomendacao da Expo de consultar push
receipts aproximadamente 15 minutos depois do envio. O filtro e feito no
SQLite antes de qualquer chamada de receipts, portanto tickets novos nao
provocam polling remoto precoce.

## Processo supervisionado

O `OrquestradorRuntime` inicia e monitora `push_dispatcher_runtime.py` apenas
quando a feature flag esta ativa. Se o filho encerrar inesperadamente, o
supervisor respeita um atraso antes de reiniciar.

No shutdown do Runtime Unificado, o filho tambem e encerrado.

## Fronteiras desta fase

Esta fase:

- nao habilita o Push Dispatcher no `.env` local;
- nao envia push real;
- nao executa smoke real;
- nao grava tokens em logs;
- nao faz chamadas externas nos testes.

O proximo passo e um smoke real controlado usando o dispositivo ja registrado,
sem imprimir o token.

## Hardening de processing stale

O runtime revisa itens da outbox que permaneceram em `processing` alem da janela usada
para receipts. A recuperacao e conservadora:

- se qualquer tentativa historica ja possui receipt `ok`, a outbox e marcada como entregue;
- se a tentativa atual possui ticket `ok` sem receipt, o item continua em `processing` e
  nao e reenviado;
- se a tentativa atual terminou apenas com erros persistidos, o item e reconciliado para
  retry ou falha terminal conforme o codigo do provedor;
- se nao existe registro de delivery para a tentativa atual, o item volta para retry apos
  a janela stale.

Existe uma janela inevitavel entre a aceitacao remota do envio e a persistencia local do
ticket. Se o processo morrer exatamente nessa janela, o resultado remoto e desconhecido e
a recuperacao pode reenviar a notificacao. Portanto essa janela possui semantica
at-least-once e pode, em caso raro de crash, produzir duplicata. Tickets aceitos e
persistidos nunca sao reenviados enquanto aguardam receipt.
