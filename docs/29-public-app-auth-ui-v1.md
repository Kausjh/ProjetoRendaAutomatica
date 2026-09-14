# Fase 2 — Etapa 2 — Public App Auth UI V1

## Objetivo

Este bloco transforma a fundação de autenticação em um fluxo utilizável no
Android.

Rotas:

```text
/            gate inicial
/connection  configuração local do alpha
/login       login
/register    cadastro
/home        área autenticada inicial
```

## Gate inicial

`/` decide o destino do usuário.

A ordem é:

1. verificar se a configuração local da API existe;
2. se não existir, abrir `/connection`;
3. enquanto a sessão é restaurada, mostrar loading;
4. usuário autenticado vai para `/home`;
5. usuário anônimo vai para `/login`;
6. falha transitória de restauração mostra retry sem apagar a sessão.

## Configuração local do alpha

O MVP ainda opera sobre o transporte privado definido na arquitetura.

Por isso `/connection` permite configurar localmente:

- URL completa da Application API terminando em `/api/v1`;
- Bearer de infraestrutura.

Nenhum endpoint real é pré-gravado.

O Bearer usa `secureTextEntry`, fica no Expo Secure Store e nunca volta a ser
renderizado pela tela depois de salvo.

Ao trocar endpoint ou Bearer, a sessão de usuário local é removida antes da
nova restauração. Isso impede que uma sessão de um backend seja carregada
contra outro backend.

A validação de domínio continua recusando a porta administrativa `8765`.

## Login

A tela de login envia:

```json
{
  "email": "...",
  "senha": "..."
}
```

Erros da API são mostrados ao usuário sem expor credenciais.

Após sucesso, o Auth Session V1 salva a sessão e a tela abre `/home`.

## Cadastro

O cadastro possui:

- e-mail;
- senha;
- confirmação de senha.

Senhas diferentes são recusadas localmente.

O contrato atual não faz auto-login. Após cadastro concluído, o usuário volta
para o login.

## Área protegida

`/home` só renderiza conteúdo quando `snapshot.status` é `authenticated`.

Qualquer outro estado redireciona para o gate `/`.

O primeiro conteúdo protegido mostra apenas:

- identificação pública da conta, quando disponível;
- acesso à configuração da conexão;
- logout.

Ofertas ainda não são implementadas neste bloco.

## Logout

O botão chama o lifecycle de logout já implementado.

Mesmo se o servidor não confirmar a revogação, a sessão local é encerrada e o
usuário volta ao gate. Uma mensagem informa a falha de revogação remota.

## Fora deste bloco

Continuam fora:

- lista e detalhe de ofertas;
- histórico de preços;
- alertas;
- watchlist;
- preferências;
- Device Registration;
- Push Dispatcher;
- Personalized Feed.

O próximo bloco é `PUBLIC_APP_MVP_OFFERS_V1`.
