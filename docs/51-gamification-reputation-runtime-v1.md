# Gamification & Reputation V1 - Runtime e Reconciliacao

## Etapa 6C2

A 6C2 define a composicao operacional da gamificacao no runtime e
a reconciliacao idempotente do estado anterior a ativacao.

Este patch de codigo nao executa o runtime e nao altera o banco real.

## Ordem de ativacao

O runtime:

1. cria os services normais de identidade e personalizacao;
2. cria o repository/service de gamificacao;
3. executa a reconciliacao historica;
4. somente se a reconciliacao terminar sem falhas configura o wiring
   nos services de dominio;
5. continua a inicializacao normal da API.

Assim, uma operacao nova nunca deve comecar a gerar eventos enquanto
o baseline historico estiver inconsistente.

## Reconciliacao

Sao reconstruidos, para contas ativas:

- conta criada;
- primeiro dispositivo historico;
- existencia de preferencias;
- itens atualmente presentes na watchlist;
- preco-alvo atualmente presente na watchlist.

As mesmas chaves e semanticas do wiring da 6C1 sao usadas.

Por isso uma segunda reconciliacao retorna eventos idempotentes em
vez de duplicar XP.

## Limite da evidencia historica

Itens removidos da watchlist antes da introducao da gamificacao nao
podem ser reconstruidos porque a tabela atual remove fisicamente o
registro.

A reconciliacao nao inventa historico ausente.

## Falhas

A reconciliacao e repetivel.

Se houver evento com status `limited`, `conflict` ou `error`, o
resultado e incompleto e o wiring nao e ativado naquela inicializacao.

O runtime principal continua disponivel sem gamificacao.

Eventos ja gravados permanecem idempotentes e uma proxima
inicializacao pode completar o restante.

## Banco de producao

A implementacao e os testes usam bancos temporarios.

A primeira mutacao deliberada de
`database/user_identity.sqlite3` sera feita somente depois do commit
da 6C2, com backup, verificacao de hash e auditoria pos-reconciliacao.

## Fronteiras

A 6C2 ainda nao expoe perfil, XP, nivel ou conquistas pela API e nao
altera o Public App.

Community Discovery, reputacao comunitaria, missoes, scoring de
ofertas e Price Intelligence continuam fora desta etapa.

## Proximo passo

Depois do commit, executar a reconciliacao controlada no banco real,
esperando no estado atual 7 eventos, 140 XP e nivel 2.
