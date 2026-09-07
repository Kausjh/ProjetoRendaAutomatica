import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

# 63.8738, -149.7525


class ShopeeApiService:
    ENDPOINT = "https://open-api.affiliate.shopee.com.br/graphql"

    def __init__(
        self,
        app_id: str | None = None,
        secret: str | None = None,
        timeout_segundos: float = 30.0,
    ) -> None:
        self.app_id = (app_id if app_id is not None else os.getenv("SHOPEE_APP_ID", "")).strip()

        self.secret = (secret if secret is not None else os.getenv("SHOPEE_SECRET", "")).strip()

        self.timeout_segundos = timeout_segundos

    def buscar_produtos(
        self,
        termo: str,
        limite: int = 20,
        pagina: int = 1,
        tipo_ordenacao: int = 1,
    ) -> list[dict[str, Any]]:
        termo_normalizado = termo.strip()

        if not termo_normalizado:
            raise ValueError("O termo de busca da Shopee n?o pode ficar vazio.")

        if limite < 1 or limite > 500:
            raise ValueError("O limite da Shopee precisa ficar entre 1 e 500.")

        if pagina < 1:
            raise ValueError("A p?gina da Shopee precisa ser maior ou igual a 1.")

        if tipo_ordenacao not in {1, 2, 3, 4, 5}:
            raise ValueError("O tipo de ordena??o da Shopee precisa ficar entre 1 e 5.")

        termo_graphql = json.dumps(
            termo_normalizado,
            ensure_ascii=False,
        )

        query = f"""
{{
  productOfferV2(
    keyword: {termo_graphql}
    sortType: {tipo_ordenacao}
    page: {pagina}
    limit: {limite}
  ) {{
    nodes {{
      itemId
      productName
      productLink
      offerLink
      imageUrl
      priceMin
      priceMax
      priceDiscountRate
      sales
      ratingStar
      commissionRate
      shopId
      shopName
    }}
    pageInfo {{
      page
      limit
      hasNextPage
    }}
  }}
}}
"""

        resposta = self._executar_graphql(query)

        dados = resposta.get("data")

        if not isinstance(dados, dict):
            raise RuntimeError("A Shopee n?o retornou o campo 'data' esperado.")

        resultado = dados.get("productOfferV2")

        if not isinstance(resultado, dict):
            raise RuntimeError("A Shopee n?o retornou 'productOfferV2' corretamente.")

        produtos = resultado.get("nodes")

        if produtos is None:
            return []

        if not isinstance(produtos, list):
            raise RuntimeError("A Shopee retornou uma lista de produtos inv?lida.")

        return [produto for produto in produtos if isinstance(produto, dict)]

    def buscar_produto_por_id(
        self,
        item_id: int | str,
        shop_id: int | str | None = None,
    ) -> dict[str, Any] | None:
        try:
            item_id_int = int(item_id)
        except (TypeError, ValueError) as erro:
            raise ValueError("O itemId da Shopee precisa ser numerico.") from erro

        if item_id_int <= 0:
            raise ValueError("O itemId da Shopee precisa ser positivo.")

        shop_id_int = None

        if shop_id is not None:
            try:
                shop_id_int = int(shop_id)
            except (TypeError, ValueError) as erro:
                raise ValueError("O shopId da Shopee precisa ser numerico.") from erro

            if shop_id_int <= 0:
                raise ValueError("O shopId da Shopee precisa ser positivo.")

        argumentos = [
            f"itemId: {item_id_int}",
        ]

        if shop_id_int is not None:
            argumentos.append(f"shopId: {shop_id_int}")

        argumentos.extend(
            [
                "sortType: 1",
                "page: 1",
                "limit: 10",
            ]
        )

        argumentos_graphql = "\n".join(f"    {argumento}" for argumento in argumentos)

        query = (
            "{\n"
            "  productOfferV2(\n"
            f"{argumentos_graphql}\n"
            "  ) {\n"
            "    nodes {\n"
            "      itemId\n"
            "      productName\n"
            "      productLink\n"
            "      offerLink\n"
            "      imageUrl\n"
            "      priceMin\n"
            "      priceMax\n"
            "      priceDiscountRate\n"
            "      sales\n"
            "      ratingStar\n"
            "      commissionRate\n"
            "      shopId\n"
            "      shopName\n"
            "    }\n"
            "    pageInfo {\n"
            "      page\n"
            "      limit\n"
            "      hasNextPage\n"
            "    }\n"
            "  }\n"
            "}\n"
        )

        resposta = self._executar_graphql(query)

        dados = resposta.get("data")

        if not isinstance(dados, dict):
            raise RuntimeError("A Shopee nao retornou o campo " "'data' esperado.")

        oferta = dados.get("productOfferV2")

        if not isinstance(oferta, dict):
            raise RuntimeError("A Shopee nao retornou " "'productOfferV2' corretamente.")

        produtos = oferta.get("nodes")

        if not isinstance(produtos, list):
            raise RuntimeError("A Shopee retornou uma lista " "de produtos invalida.")

        exatos = []

        for produto in produtos:
            if not isinstance(
                produto,
                dict,
            ):
                continue

            if str(produto.get("itemId")).strip() != str(item_id_int):
                continue

            if shop_id_int is not None and str(produto.get("shopId")).strip() != str(shop_id_int):
                continue

            exatos.append(produto)

        if not exatos:
            return None

        identidades = {
            (
                str(produto.get("shopId") or "").strip(),
                str(produto.get("itemId") or "").strip(),
            )
            for produto in exatos
        }

        if len(identidades) != 1:
            raise RuntimeError("A Shopee retornou mais de uma " "identidade para o mesmo produto.")

        return exatos[0]

    def gerar_shortlink(self, link_original: str) -> str:
        link_normalizado = link_original.strip()

        if not link_normalizado:
            raise ValueError("O link original da Shopee n?o pode ficar vazio.")

        link_graphql = json.dumps(
            link_normalizado,
            ensure_ascii=False,
        )

        query = f"""
mutation {{
  generateShortLink(
    input: {{
      originUrl: {link_graphql}
    }}
  ) {{
    shortLink
  }}
}}
"""

        resposta = self._executar_graphql(query)

        dados = resposta.get("data", {})
        resultado = dados.get("generateShortLink") or {}
        shortlink = resultado.get("shortLink")

        if not isinstance(shortlink, str) or not shortlink.strip():
            raise RuntimeError("A Shopee n?o retornou um shortlink afiliado v?lido.")

        return shortlink.strip()

    def _executar_graphql(self, query: str) -> dict[str, Any]:
        self._validar_credenciais()

        payload = json.dumps(
            {"query": query},
            ensure_ascii=False,
            separators=(",", ":"),
        )

        timestamp = str(int(time.time()))

        assinatura = hashlib.sha256(
            (f"{self.app_id}" f"{timestamp}" f"{payload}" f"{self.secret}").encode()
        ).hexdigest()

        authorization = (
            f"SHA256 Credential={self.app_id}, "
            f"Timestamp={timestamp}, "
            f"Signature={assinatura}"
        )

        requisicao = urllib.request.Request(
            self.ENDPOINT,
            data=payload.encode("utf-8"),
            headers={
                "Authorization": authorization,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                requisicao,
                timeout=self.timeout_segundos,
            ) as resposta:
                corpo = resposta.read().decode("utf-8")
                resultado = json.loads(corpo)

        except urllib.error.HTTPError as erro:
            corpo_erro = erro.read().decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                "A Shopee Open API respondeu com " f"HTTP {erro.code}: {corpo_erro}"
            ) from erro

        except urllib.error.URLError as erro:
            raise RuntimeError(f"Falha de conex?o com a Shopee Open API: {erro}") from erro

        except json.JSONDecodeError as erro:
            raise RuntimeError("A Shopee Open API retornou uma resposta JSON inv?lida.") from erro

        erros = resultado.get("errors")

        if erros:
            mensagens = []

            for erro in erros:
                if isinstance(erro, dict):
                    mensagem = erro.get("message")

                    if mensagem:
                        mensagens.append(str(mensagem))

            detalhe = "; ".join(mensagens) or str(erros)

            raise RuntimeError(f"A Shopee Open API retornou erro: {detalhe}")

        return resultado

    def _validar_credenciais(self) -> None:
        if not self.app_id:
            raise ValueError("SHOPEE_APP_ID n?o est? configurado.")

        if not self.secret:
            raise ValueError("SHOPEE_SECRET n?o est? configurado.")
