# Etapa 3 — Device Registration V1 — Fase B

## Objetivo

Esta fase liga o Public App ao backend de Device Registration V1 sem implementar
a entrega de push.

O aplicativo passa a ter uma identidade estável de instalação, consegue adquirir
um Expo Push Token quando executado em um build compatível e registra esse token
nas rotas autenticadas de `/me/devices`.

## Identidade da instalação

O `instalacao_id` é um UUID v4 gerado uma única vez pelo aplicativo e persistido
no `expo-secure-store`.

Chave local:

`pra_public_installation_id_v1`

A identidade da instalação não é a sessão do usuário e não é apagada no logout.

## Cliente HTTP

O `PublicApiClient` passa a cobrir:

- `GET /me/devices`;
- `PUT /me/devices/{instalacao_id}`;
- `DELETE /me/devices/{instalacao_id}`.

Todas essas chamadas exigem a sessão `X-User-Session`, já gerenciada pelo
transporte existente.

O cliente nunca envia `conta_id`.

## Aquisição do token

O aplicativo usa `expo-notifications` e o Expo Push Service.

O fluxo:

1. ignora plataformas não móveis;
2. detecta Expo Go e adia o binding sem quebrar o aplicativo;
3. exige um `projectId` real do projeto Expo/EAS;
4. no Android, cria o canal `ofertas`;
5. verifica e, se necessário, solicita permissão;
6. obtém o Expo Push Token;
7. envia o token ao backend;
8. não imprime, renderiza ou persiste o token no app.

## Expo Go

Push remoto não é suportado pelo Expo Go no Android nas versões atuais do Expo
SDK. O aplicativo continua funcional em Expo Go, mas o binding fica adiado com
o motivo `expo-go-remote-push-unavailable`.

A validação de token real exige um development build.

## Bootstrap autenticado

`DeviceRegistrationBootstrap` observa o estado da sessão.

Quando a sessão passa a `authenticated`, o aplicativo tenta registrar a
instalação. Isso cobre tanto restauração de sessão no boot quanto login.

O backend é idempotente por `conta_id + instalacao_id`, então repetir a operação
também cobre rotação de token.

## Logout

No logout explícito, o aplicativo tenta revogar a instalação antes de invalidar
a sessão.

Falha de rede na revogação do dispositivo não bloqueia o logout local.

## Fronteiras

Esta fase ainda não:

- envia notificações;
- implementa Push Dispatcher;
- adiciona credenciais FCM ao repositório;
- inventa ou versiona `projectId` fictício;
- valida token remoto real dentro do Expo Go.

O próximo passo é configurar o projeto/credenciais de desenvolvimento, gerar um
development build e validar um Expo Push Token real chegando ao backend.
