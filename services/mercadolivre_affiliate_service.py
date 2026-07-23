from urllib.parse import urldefrag

import httpx

from services.browser.cookie_manager import (
    CookieManager,
)


class MercadoLivreAffiliateService:

    API_URL = (
        "https://www.mercadolivre.com.br/"
        "affiliate-program/api/v2/"
        "stripe/user/links"
    )

    TAG_AFILIADO_PADRAO = (
        "jhonataskaue20230315123251"
    )

    def __init__(
        self,
        cookie_manager: CookieManager | None = None,
        timeout_segundos: float = 30.0,
    ) -> None:

        self.cookie_manager = (
            cookie_manager
            or CookieManager()
        )

        self.timeout_segundos = (
            timeout_segundos
        )

    def gerar(
        self,
        url: str,
        tag: str | None = None,
    ) -> str | None:

        url_normalizada = (
            self._normalizar_url(url)
        )

        if not url_normalizada:
            return None

        tag_utilizada = (
            tag
            or self.TAG_AFILIADO_PADRAO
        )

        for tentativa in range(2):

            forcar_atualizacao = (
                tentativa > 0
            )

            cookies = (
                self.cookie_manager
                .obter_cookies(
                    forcar_atualizacao=(
                        forcar_atualizacao
                    )
                )
            )

            resposta = self._enviar_requisicao(
                url=url_normalizada,
                tag=tag_utilizada,
                cookies=cookies,
            )

            if resposta.status_code in {
                401,
                403,
            }:

                self.cookie_manager.invalidar_cache()

                if tentativa == 0:
                    continue

            return self._processar_resposta(
                resposta
            )

        return None

    def _enviar_requisicao(
        self,
        url: str,
        tag: str,
        cookies: dict[str, str],
    ) -> httpx.Response:

        headers = {
            "Accept": (
                "application/json, "
                "text/plain, */*"
            ),
            "Content-Type": "application/json",
            "Origin": (
                "https://www.mercadolivre.com.br"
            ),
            "Referer": (
                "https://www.mercadolivre.com.br/"
                "affiliate-program"
            ),
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/149.0.0.0 "
                "Safari/537.36"
            ),
        }

        payload = {
            "tag": tag,
            "url": url,
        }

        return httpx.post(
            self.API_URL,
            headers=headers,
            cookies=cookies,
            json=payload,
            timeout=self.timeout_segundos,
            follow_redirects=True,
        )

    def _processar_resposta(
        self,
        resposta: httpx.Response,
    ) -> str | None:

        if resposta.status_code != 200:

            mensagem = self._extrair_mensagem_erro(
                resposta
            )

            print(
                "[MercadoLivreAfiliados] "
                f"Falha HTTP {resposta.status_code}: "
                f"{mensagem}"
            )

            return None

        try:
            dados = resposta.json()

        except ValueError:

            print(
                "[MercadoLivreAfiliados] "
                "A API retornou uma resposta "
                "que não é um JSON válido."
            )

            return None

        link_afiliado = dados.get(
            "short_url"
        )

        if not isinstance(
            link_afiliado,
            str
        ):
            return None

        link_afiliado = (
            link_afiliado.strip()
        )

        if not link_afiliado.startswith(
            "https://meli.la/"
        ):
            return None

        return link_afiliado

    def _extrair_mensagem_erro(
        self,
        resposta: httpx.Response,
    ) -> str:

        try:
            dados = resposta.json()

        except ValueError:
            return resposta.text.strip()

        erro = dados.get(
            "error"
        )

        if isinstance(
            erro,
            dict
        ):
            mensagem = erro.get(
                "message"
            )

            if isinstance(
                mensagem,
                str
            ):
                return mensagem

        return str(dados)

    def _normalizar_url(
        self,
        url: str,
    ) -> str:

        url_limpa = url.strip()

        if not url_limpa:
            return ""

        url_sem_fragmento, _ = urldefrag(
            url_limpa
        )

        return url_sem_fragmento