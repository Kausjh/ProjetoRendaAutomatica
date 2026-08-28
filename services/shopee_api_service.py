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
