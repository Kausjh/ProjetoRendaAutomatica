# Fase 2 — Etapa 2 — Public App MVP: arquitetura e escopo V1

## Decisão

O Public App MVP será um aplicativo **Android de usuário final** implementado em:

- React Native;
- Expo;
- TypeScript;
- Expo Router;
- TanStack Query;
- Expo Secure Store;
- `StyleSheet` nativo para UI nesta primeira versão.

O código do app público poderá viver neste repositório em:

```text
apps/public-mobile/
```

O aplicativo Android privado de administração continua fora deste repositório.

## Por que Expo neste MVP

O ambiente atual já possui Android SDK, ADB, Node, NPM e NPX. O Java disponível
é Java 8 e não existe Gradle global configurado.

Expo permite iniciar a camada de produto e testar o fluxo no Android sem
bloquear a etapa inteira na preparação imediata de um toolchain Gradle/JDK
moderno.

Um build Android nativo independente poderá exigir JDK mais novo posteriormente;
isso será tratado quando o build local nativo passar a ser necessário.

## Papel do aplicativo

"Public App" significa **aplicativo voltado ao usuário final**, e não que o MVP
já estará pronto para distribuição pública irrestrita na Internet.

Nesta etapa, a distribuição operacional será:

```text
internal alpha over tailnet
```

O objetivo é validar o produto real usando a User-Facing API V1 já concluída.

## Transporte atual

O perfil atual é:

```text
Android
  -> Tailscale :18767
  -> TCP forwarder
  -> 127.0.0.1:8766
  -> /api/v1
```

A porta administrativa `8765` é proibida para o Public App.

O app não deve conhecer, reproduzir nem acessar regras do painel administrativo.

## Segredo de infraestrutura

O `API_APLICACAO_TOKEN` não pode:

- ser hardcoded;
- ser commitado;
- ser incluído no bundle como segredo fixo;
- aparecer em logs.

No alpha sobre Tailscale, ele será fornecido por configuração local de runtime.

A sessão do usuário é outra credencial, independente, enviada em:

```http
X-User-Session: pra_usr_v1_<token>
```

Ela será persistida no Android via Expo Secure Store.

## Abstração de transporte

A UI e os casos de uso não podem depender diretamente de Tailscale, IP, porta
ou headers de infraestrutura.

A camada de rede terá um `TransportConfig`/API client isolado.

Perfil atual:

```text
tailscale-http-trusted-tunnel
```

Perfil futuro previsto:

```text
public-https-gateway
```

Assim, a futura mudança de transporte não exigirá reescrever telas e regras de
apresentação.

## Escopo funcional do MVP

### Autenticação

- cadastro;
- login;
- logout;
- restauração de sessão local.

Rotas:

```text
POST /api/v1/auth/register
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/me
```

### Ofertas

- lista de produtos;
- detalhe do produto;
- histórico de preço.

Rotas:

```text
GET /api/v1/produtos
GET /api/v1/produtos/{canonical_key}
GET /api/v1/produtos/{canonical_key}/historico
```

### Alertas

- lista de alertas da API atual.

Rota:

```text
GET /api/v1/alertas
```

Nesta etapa, isso não significa push notification.

### Watchlist

- listar;
- adicionar/atualizar;
- remover.

### Conta e preferências

- dados da conta;
- notificações de preço habilitadas/desabilitadas;
- marketplaces preferidos.

## Navegação proposta

Estrutura de alto nível:

```text
Auth
  Login
  Cadastro

App
  Ofertas
  Alertas
  Watchlist
  Conta
```

Detalhe de produto é uma rota interna a partir de Ofertas/Watchlist.

## Fonte da verdade

A API continua sendo a fonte da verdade.

O app não deve duplicar:

- regras de curadoria;
- regras de preço;
- regras de matching;
- autorização de conta;
- lógica do Alert Engine.

## Fora do MVP

Não entram nesta Etapa 2:

- Device Registration V1;
- Push Dispatcher V1;
- Personalized Feed V1;
- painel administrativo;
- API administrativa `8765`;
- exposição pública direta da porta `8766`;
- segredo de infraestrutura embutido no app.

Esses itens pertencem a etapas posteriores ou a outra superfície do produto.

## Ordem de implementação

1. bootstrap Expo + TypeScript;
2. API client e abstração de transporte;
3. Secure Store para sessão;
4. cadastro/login/logout;
5. ofertas + detalhe + histórico;
6. watchlist;
7. conta + preferências;
8. alertas;
9. smoke test no Android via Tailscale;
10. audit final do MVP.

O próximo bloco é o bootstrap do app.
