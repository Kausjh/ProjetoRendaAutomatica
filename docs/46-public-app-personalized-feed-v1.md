# Public App Personalized Feed V1

## Fase 5C1 - Data Layer

Esta fase conecta o Public App ao endpoint autenticado:

`GET /api/v1/me/feed`

Ela ainda nao substitui visualmente a Home.

O metodo `getPersonalizedFeed` reutiliza o mesmo `HttpApiTransport` do app,
preservando o Bearer da infraestrutura, `X-User-Session`, timeout e envelope
User-Facing API V1.

O modulo `src/feed` possui tipos, presenter e React Query hook dedicados.
O hook aceita `enabled` para aguardar a sessao autenticada antes de consultar
a rota de usuario.

A Fase 5C1 nao altera `home.tsx`, backend, Push Dispatcher ou arquivos Expo
locais. Tambem nao usa a lista generica de produtos como falso fallback
personalizado.

## Proximo passo

A Fase 5C2 substituira a fonte principal da Home pelo feed real e exibira os
motivos de relevancia mantendo acesso ao detalhe pela `canonicalKey`.
