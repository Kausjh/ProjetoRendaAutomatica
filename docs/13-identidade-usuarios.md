# Bloco 27 — User Identity Foundation V1

## Objetivo

Criar a fundação de identidade de usuários finais para a futura plataforma
pública sem alterar o contrato read-only da Application API V1.

O roadmap da plataforma pública lista, depois da API própria, contas de
usuários, preferências, watchlists, notificações, feed personalizado e
clientes públicos. Esta camada existe para impedir que autenticação de
infraestrutura seja reutilizada indevidamente como identidade de usuário.

## Escopo

O Bloco 27 introduz:

- conta persistente identificada por email normalizado;
- senha armazenada somente como hash derivado com `scrypt` e salt individual;
- sessão com token aleatório;
- persistência somente do SHA-256 do token de sessão;
- validade temporal;
- revogação explícita;
- resolução de sessão para conta ativa.

O banco padrão futuro é:

`database/user_identity.sqlite3`

## Fronteiras de segurança

Este bloco não cria rotas HTTP.

A Application API V1 permanece read-only e seus métodos mutantes continuam
fora do contrato.

O Bearer usado para proteger o transporte/API de aplicação é uma credencial
de infraestrutura e não representa uma conta de usuário.

A API administrativa da porta 8765 também não representa identidade pública.

O aplicativo Android administrativo privado não é o futuro aplicativo
público de usuários.

## Por que não expor rotas ainda

Cadastro, login e recuperação de conta formam uma superfície de segurança
própria. Primeiro consolidamos persistência, hashing, sessões e limites de
domínio. A exposição em rede deve acontecer em uma etapa posterior com
contrato e testes específicos.

## Próximas capacidades habilitadas

A identidade de usuário permite implementar, sem acoplamento ao admin:

- preferências;
- watchlists;
- feed personalizado;
- notificações;
- clientes públicos.

## Critérios de aceite

1. contas possuem identidade persistente;
2. emails são normalizados e únicos;
3. senha em texto puro nunca é persistida;
4. cada conta usa salt próprio;
5. autenticação correta funciona e senha incorreta falha fechada;
6. tokens de sessão são aleatórios;
7. token em texto puro nunca é persistido;
8. sessão expirada não autentica;
9. sessão revogada não autentica;
10. nenhuma nova rota de rede é criada;
11. `/api/v1` continua read-only;
12. admin, Bearer de infraestrutura e identidade de usuário permanecem
    domínios separados.
