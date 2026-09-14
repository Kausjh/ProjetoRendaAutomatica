# Fase 2 — Etapa 2 — Public App Auth Session V1

## Objetivo

Este bloco cria o estado real de autenticação do aplicativo público.

A implementação vive em:

```text
apps/public-mobile/src/auth/
```

Ainda não são criadas as telas finais de login e cadastro.

## Estados

O provider expõe quatro estados:

```text
restoring
anonymous
authenticated
error
```

`restoring` é usado enquanto o app verifica uma sessão previamente salva.

`anonymous` significa que não existe sessão local válida.

`authenticated` mantém em memória a conta retornada por `/me` ou `login`.

`error` representa falha transitória durante restauração/refresh sem apagar
automaticamente uma sessão local potencialmente válida.

## Restauração

Ao montar o app:

1. a sessão é lida do Expo Secure Store;
2. se não houver token, o estado passa para `anonymous`;
3. se houver token, o app chama `GET /me`;
4. `401` é tratado como sessão inválida e remove o token local;
5. erros de rede/timeout não removem o token local.

Isso evita deslogar o usuário só porque o backend está temporariamente
indisponível.

## Cadastro

`register` usa `POST /auth/register`.

O contrato atual não faz auto-login, portanto o cadastro retorna a conta criada
e mantém o estado de autenticação inalterado.

## Login

`login` usa `POST /auth/login`.

Após sucesso:

1. valida que `sessao.token` existe;
2. salva o token no Secure Store;
3. move o provider para `authenticated`;
4. mantém a conta retornada em memória.

## Logout

`logout` tenta revogar a sessão atual no servidor por `POST /auth/logout`.

A sessão local é removida em `finally`, mesmo se o servidor estiver
indisponível. Isso garante logout local imediato.

Se a revogação remota falhar, o erro ainda é devolvido para a futura UI poder
informar o usuário.

## Refresh da conta

`refreshMe` permite revalidar `/me`.

`401` remove sessão e volta para `anonymous`.

Falha transitória preserva a sessão local e passa o estado para `error`.

## Integração no root

`app/_layout.tsx` passa a envolver a navegação com:

```text
QueryClientProvider
  AuthSessionProvider
    AuthSessionBootstrap
      Stack
```

O app agora está preparado para o próximo bloco: telas e roteamento de
autenticação.

## Fora deste bloco

Continuam fora:

- telas finais de login/cadastro;
- formulários;
- navegação condicional visual;
- Device Registration;
- Push Dispatcher;
- Personalized Feed;
- qualquer acesso à API administrativa.

O próximo bloco é `PUBLIC_APP_MVP_AUTH_UI_V1`.
