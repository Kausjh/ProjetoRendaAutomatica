# Fase 2 — Etapa 2 — Public App MVP Bootstrap V1

## Resultado

O primeiro código do aplicativo público passa a existir em:

```text
apps/public-mobile/
```

A fundação usa:

- React Native;
- Expo;
- Expo Router;
- TypeScript estrito;
- TanStack Query;
- Expo Secure Store.

## Estado deste bloco

Este bloco cria somente a fundação do aplicativo.

Ainda não existe API client funcional nem tela de login real.

A tela inicial serve como smoke visual para confirmar que o bundle sobe.

## Segurança

Nenhum `API_APLICACAO_TOKEN` é incluído no código, no `app.json`, no
`.env.example` ou em variável `EXPO_PUBLIC_*`.

O alpha terá configuração local de:

- base URL da Application API;
- token de infraestrutura;
- sessão do usuário.

Esses valores são persistidos via Secure Store.

## Estrutura inicial

```text
apps/public-mobile/
  app/
    _layout.tsx
    index.tsx
  src/
    config/
      runtime-config.ts
    storage/
      secure-runtime-config.ts
  .env.example
  .gitignore
  app.json
  expo-env.d.ts
  package.json
  package-lock.json
  tsconfig.json
```

## Próximo bloco

O próximo bloco implementa o API client e a abstração real de transporte,
mantendo Tailscale/porta/headers fora da UI.
