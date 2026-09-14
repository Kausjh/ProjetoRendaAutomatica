# User-Facing API V1 — Abuse Controls V1

## Escopo

Este bloco protege somente:

- `POST /api/v1/auth/register`;
- `POST /api/v1/auth/login`.

As rotas autenticadas `/me`, preferences, watchlist e logout não entram no
rate limiting desta V1.

## Estratégia

O limiter usa janela deslizante em memória e `time.monotonic()`.

Ele é protegido por `threading.Lock`, portanto é seguro dentro do
`ThreadingHTTPServer` atual.

Não existe coordenação entre múltiplos processos ou múltiplas máquinas nesta
versão. Isso é intencional: o runtime atual é single-process.

## Register

Default:

- 5 tentativas;
- janela de 3600 segundos;
- chave: endereço do cliente observado diretamente pelo servidor.

## Login

Defaults:

- 20 tentativas por endereço de cliente;
- 10 tentativas por email normalizado;
- janela de 300 segundos.

O limitador por email ajuda contra tentativas direcionadas à mesma conta sem
mudar a resposta genérica de credenciais inválidas.

## Resposta HTTP

Quando limitado:

- status `429`;
- código `limite_requisicoes_excedido`;
- header `Retry-After` em segundos;
- `Cache-Control: no-store`.

A proteção de infraestrutura é verificada antes do limiter. Assim, uma
requisição que nem sequer passa pelo Bearer de infraestrutura não consome o
budget de autenticação do usuário.

## Configuração

Variáveis opcionais:

```text
API_USER_REGISTER_RATE_LIMIT=5
API_USER_REGISTER_RATE_WINDOW_SECONDS=3600
API_USER_LOGIN_RATE_LIMIT=20
API_USER_LOGIN_SUBJECT_RATE_LIMIT=10
API_USER_LOGIN_RATE_WINDOW_SECONDS=300
```

Todos os valores precisam ser inteiros positivos.

## Limites desta V1

- estado não persistido;
- reset ao reiniciar o processo;
- sem Redis;
- sem coordenação multi-processo;
- sem confiar em `X-Forwarded-For` ou headers de proxy.

O identificador de cliente é `client_address` do próprio
`BaseHTTPRequestHandler`.

O próximo passo é o audit final da Etapa 1 da User-Facing API V1.
