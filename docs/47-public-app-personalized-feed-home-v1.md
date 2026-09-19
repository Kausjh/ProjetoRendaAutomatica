# Public App Personalized Feed V1 - Home

## Fase 5C2

A Home passa a consumir o feed autenticado real por meio de
`usePersonalizedFeed`.

A lista generica de produtos deixa de ser a fonte principal da Home.

## Experiencia

A tela mostra apenas oportunidades que possuem sinal real da conta.

Os motivos podem incluir:

- produto na Lista;
- preco-alvo atingido;
- marketplace preferido.

A pontuacao numerica interna de relevancia nao e mostrada ao usuario.

## Compatibilidade

Foram preservados:

- acesso ao detalhe do produto;
- adicionar e remover da Lista diretamente pela Home;
- pull-to-refresh;
- busca generica em `/search`;
- navegacao inferior existente.

O item personalizado e adaptado para o card visual existente, evitando
reescrever a identidade visual do Public App.

## Estado vazio

A Home nao finge personalizacao usando o catalogo generico.

Sem sinais personalizados, o estado vazio orienta o usuario a adicionar
produtos a Lista ou definir marketplaces preferidos.

## Fronteiras

A Fase 5C2 nao altera:

- backend;
- Push Dispatcher;
- rota de busca generica;
- arquivos Expo gerados localmente.

## Proximo passo

Executar validacao final da Fase 5 e smoke no dispositivo real antes de
considerar o Personalized Feed V1 concluido de ponta a ponta.
