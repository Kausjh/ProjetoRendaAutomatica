# 63.8738, -149.7525

from __future__ import annotations

import logging
from collections.abc import Iterable

from playwright.sync_api import (
    Error as PlaywrightError,
)
from playwright.sync_api import (
    Page,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)

from services.validador_preco_aliexpress import (
    ResultadoPrecoAliExpress,
    ValidadorPrecoAliExpress,
)

logger = logging.getLogger(__name__)


class AliExpressPrecoCdpService:
    ENDPOINT_CDP = "http://127.0.0.1:9222"

    ENDPOINT_PDP = "mtop.aliexpress.pdp.pc.query"

    URL_PRODUTO = "https://pt.aliexpress.com/" "item/{produto_id}.html"

    def __init__(
        self,
        validador: ValidadorPrecoAliExpress | None = None,
        endpoint_cdp: str = ENDPOINT_CDP,
        timeout_navegacao_ms: int = 90_000,
        espera_pos_carga_ms: int = 2_500,
    ) -> None:
        endpoint_cdp = endpoint_cdp.strip()

        if not endpoint_cdp:
            raise ValueError("endpoint_cdp nao pode ser vazio.")

        if timeout_navegacao_ms <= 0:
            raise ValueError("timeout_navegacao_ms precisa " "ser maior que zero.")

        if espera_pos_carga_ms < 0:
            raise ValueError("espera_pos_carga_ms nao pode " "ser negativa.")

        self.validador = validador if validador is not None else ValidadorPrecoAliExpress()

        self.endpoint_cdp = endpoint_cdp

        self.timeout_navegacao_ms = timeout_navegacao_ms

        self.espera_pos_carga_ms = espera_pos_carga_ms

    def validar_produtos(
        self,
        produto_ids: Iterable[str],
    ) -> dict[
        str,
        ResultadoPrecoAliExpress,
    ]:
        ids = self._normalizar_ids(produto_ids)

        if not ids:
            return {}

        logger.info(
            "Conectando ao Chrome/CDP para " "validar %s produto(s) AliExpress.",
            len(ids),
        )

        with sync_playwright() as playwright:
            navegador = playwright.chromium.connect_over_cdp(
                self.endpoint_cdp,
                timeout=30_000,
            )

            if not navegador.contexts:
                raise RuntimeError("Chrome/CDP conectado, mas " "nenhum contexto foi encontrado.")

            contexto = navegador.contexts[0]

            pagina = contexto.new_page()

            pagina.set_default_timeout(15_000)

            try:
                return self.validar_produtos_com_pagina(
                    pagina=pagina,
                    produto_ids=ids,
                )

            finally:
                if not pagina.is_closed():
                    pagina.close()

        # A conexao CDP pertence ao runtime.
        # Nao chamamos navegador.close().

    def validar_produtos_com_pagina(
        self,
        pagina: Page,
        produto_ids: Iterable[str],
    ) -> dict[
        str,
        ResultadoPrecoAliExpress,
    ]:
        ids = self._normalizar_ids(produto_ids)

        resultados: dict[
            str,
            ResultadoPrecoAliExpress,
        ] = {}

        for indice, produto_id in enumerate(
            ids,
            start=1,
        ):
            if not produto_id.isdigit():
                resultados[produto_id] = self._rejeitar(
                    produto_id,
                    "produto_id invalido",
                )

                continue

            logger.debug(
                "Validando AliExpress %s/%s: %s.",
                indice,
                len(ids),
                produto_id,
            )

            resultado = self._validar_produto_na_pagina(
                pagina=pagina,
                produto_id=produto_id,
            )

            resultados[produto_id] = resultado

        return resultados

    def _validar_produto_na_pagina(
        self,
        pagina: Page,
        produto_id: str,
    ) -> ResultadoPrecoAliExpress:
        url = self.URL_PRODUTO.format(produto_id=produto_id)

        estado: dict[
            str,
            str | None,
        ] = {
            "pdp": None,
        }

        def capturar_pdp(
            resposta,
        ) -> None:
            if self.ENDPOINT_PDP not in resposta.url:
                return

            try:
                estado["pdp"] = resposta.text()
            except Exception:
                return

        pagina.on(
            "response",
            capturar_pdp,
        )

        try:
            try:
                pagina.goto(
                    url,
                    wait_until=("domcontentloaded"),
                    timeout=(self.timeout_navegacao_ms),
                )

            except PlaywrightTimeoutError:
                logger.warning(
                    "Timeout ao abrir AliExpress " "%s. Tentando validar o " "conteudo carregado.",
                    produto_id,
                )

            except PlaywrightError as erro:
                return self._rejeitar(
                    produto_id,
                    ("erro Playwright ao abrir " f"produto: {erro}"),
                )

            try:
                if self.espera_pos_carga_ms:
                    pagina.wait_for_timeout(self.espera_pos_carga_ms)

                url_final = pagina.url
                html = pagina.content()

            except PlaywrightError as erro:
                return self._rejeitar(
                    produto_id,
                    ("erro Playwright ao ler " f"produto: {erro}"),
                )

            return self.validador.validar_html(
                produto_id=produto_id,
                url_final=url_final,
                html=html,
                pdp_texto=estado["pdp"],
                exigir_pdp=True,
            )

        finally:
            try:
                pagina.remove_listener(
                    "response",
                    capturar_pdp,
                )
            except Exception:
                pass

    @staticmethod
    def _normalizar_ids(
        produto_ids: Iterable[str],
    ) -> list[str]:
        resultado: list[str] = []
        vistos: set[str] = set()

        for produto_id in produto_ids:
            texto = str(produto_id).strip()

            if not texto:
                continue

            if texto in vistos:
                continue

            vistos.add(texto)

            resultado.append(texto)

        return resultado

    @staticmethod
    def _rejeitar(
        produto_id: str,
        motivo: str,
    ) -> ResultadoPrecoAliExpress:
        return ResultadoPrecoAliExpress(
            produto_id=produto_id,
            preco_brl=None,
            moeda=None,
            url_produto=None,
            valido=False,
            motivo=motivo,
        )
