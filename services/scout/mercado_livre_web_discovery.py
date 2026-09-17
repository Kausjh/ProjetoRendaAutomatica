# 63.8738, -149.7525

from __future__ import annotations

import logging
from dataclasses import dataclass
from urllib.parse import quote_plus

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, sync_playwright
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from scrapers.mercado_livre.navegador import (
    ENDERECO_CDP,
    conectar_ao_chrome,
)
from scrapers.mercado_livre.parser import (
    extrair_id_produto,
    limpar_espacos,
    normalizar_link,
)

logger = logging.getLogger(__name__)


class ErroDiscoveryMercadoLivre(RuntimeError):
    """Falha controlada durante a descoberta web do Mercado Livre."""


@dataclass(frozen=True, slots=True)
class ResultadoDiscoveryMercadoLivre:
    identificador_ml: str
    titulo: str
    link: str


class MercadoLivreWebDiscovery:
    """
    Descobre resultados na busca publica do Mercado Livre.

    Este componente possui exclusivamente a responsabilidade de discovery.
    Ele nao substitui o cliente da API oficial e nao pertence ao scraper
    principal API-first.
    """

    URL_BUSCA = "https://lista.mercadolivre.com.br/{termo}"

    SELETORES_CARTAO = (
        "li.ui-search-layout__item",
        "li.poly-card",
        "div.ui-search-result__wrapper",
        "div.poly-card",
    )

    SELETORES_TITULO = (
        "a.poly-component__title",
        "h3.poly-component__title-wrapper",
        "h2.ui-search-item__title",
        ".ui-search-item__title",
    )

    SELETORES_LINK = (
        "a.poly-component__title",
        "h3.poly-component__title-wrapper a",
        "a.ui-search-item__group__element",
        "a[href*='produto.mercadolivre.com.br']",
        "a[href*='mercadolivre.com.br']",
    )

    INDICADORES_BLOQUEIO = (
        "captcha",
        "nao conseguimos confirmar",
        "n?o conseguimos confirmar",
        "verifique que voce e humano",
        "verifique que voc? ? humano",
        "atividade incomum",
        "acesso negado",
        "access denied",
    )

    def __init__(
        self,
        *,
        endpoint_cdp: str = ENDERECO_CDP,
        playwright_factory=sync_playwright,
        conectar_fn=conectar_ao_chrome,
    ) -> None:
        endpoint_cdp = str(endpoint_cdp or "").strip()

        if not endpoint_cdp:
            raise ValueError("endpoint_cdp nao pode ser vazio.")

        self.endpoint_cdp = endpoint_cdp
        self._playwright_factory = playwright_factory
        self._conectar_fn = conectar_fn

    def descobrir(
        self,
        consulta: str,
        *,
        limite: int = 5,
    ) -> tuple[ResultadoDiscoveryMercadoLivre, ...]:
        consulta = limpar_espacos(consulta)

        if not consulta:
            raise ValueError("consulta nao pode ser vazia.")

        if isinstance(limite, bool) or not isinstance(limite, int) or limite <= 0:
            raise ValueError("limite precisa ser inteiro maior que zero.")

        termo_url = quote_plus(consulta).replace("+", "-")

        url = self.URL_BUSCA.format(
            termo=termo_url,
        )

        logger.info(
            "Discovery web ML: consulta '%s', limite=%s.",
            consulta,
            limite,
        )

        try:
            with self._playwright_factory() as playwright:
                _, contexto, _ = self._conectar_fn(
                    playwright,
                    self.endpoint_cdp,
                )

                pagina = contexto.new_page()
                pagina.set_default_timeout(15000)

                try:
                    self._abrir_busca(
                        pagina,
                        url,
                    )

                    if self._pagina_possui_bloqueio(pagina):
                        raise ErroDiscoveryMercadoLivre("mercado_livre_web_bloqueado")

                    if not self._aguardar_cartoes(pagina):
                        logger.warning(
                            "Discovery web ML nao encontrou cards " "para '%s'.",
                            consulta,
                        )
                        return ()

                    resultados = self._extrair_resultados(
                        pagina,
                        limite=limite,
                    )

                    logger.info(
                        "Discovery web ML: %s resultado(s) para '%s'.",
                        len(resultados),
                        consulta,
                    )

                    return resultados

                finally:
                    if not pagina.is_closed():
                        pagina.close()

        except ErroDiscoveryMercadoLivre:
            raise

        except PlaywrightError as erro:
            raise ErroDiscoveryMercadoLivre("mercado_livre_web_playwright") from erro

    @staticmethod
    def _abrir_busca(
        pagina: Page,
        url: str,
    ) -> None:
        try:
            resposta = pagina.goto(
                url,
                wait_until="domcontentloaded",
                timeout=45000,
            )

            if resposta is not None:
                status_http = int(
                    getattr(
                        resposta,
                        "status",
                        0,
                    )
                    or 0
                )

                if status_http >= 400:
                    raise ErroDiscoveryMercadoLivre("mercado_livre_web_http_" f"{status_http}")

            pagina.wait_for_load_state(
                "domcontentloaded",
                timeout=15000,
            )

        except PlaywrightTimeoutError:
            logger.warning(
                "Timeout durante abertura da busca ML: %s.",
                url,
            )

        except PlaywrightError as erro:
            raise ErroDiscoveryMercadoLivre("mercado_livre_web_navegacao") from erro

    def _aguardar_cartoes(
        self,
        pagina: Page,
    ) -> bool:
        for indice, seletor in enumerate(
            self.SELETORES_CARTAO,
        ):
            timeout = 15000 if indice == 0 else 4000

            try:
                pagina.wait_for_selector(
                    seletor,
                    state="attached",
                    timeout=timeout,
                )

            except (
                PlaywrightTimeoutError,
                PlaywrightError,
            ):
                continue

            try:
                if pagina.locator(seletor).count() > 0:
                    return True

            except PlaywrightError:
                continue

        return False

    def _extrair_resultados(
        self,
        pagina: Page,
        *,
        limite: int,
    ) -> tuple[ResultadoDiscoveryMercadoLivre, ...]:
        resultados: list[ResultadoDiscoveryMercadoLivre] = []
        ids_vistos: set[str] = set()

        cartoes = self._obter_cartoes(pagina)

        quantidade = cartoes.count()

        for indice in range(quantidade):
            if len(resultados) >= limite:
                break

            cartao = cartoes.nth(indice)

            titulo = self._primeiro_texto(
                cartao,
                self.SELETORES_TITULO,
            )

            link = self._primeiro_atributo(
                cartao,
                self.SELETORES_LINK,
                "href",
            )

            titulo = limpar_espacos(titulo)
            link = normalizar_link(link)

            if not titulo or not link:
                continue

            identificador = extrair_id_produto(link)

            if not identificador:
                continue

            if identificador in ids_vistos:
                continue

            ids_vistos.add(identificador)

            resultados.append(
                ResultadoDiscoveryMercadoLivre(
                    identificador_ml=identificador,
                    titulo=titulo,
                    link=link,
                )
            )

        return tuple(resultados)

    def _obter_cartoes(
        self,
        pagina: Page,
    ):
        for seletor in self.SELETORES_CARTAO:
            cartoes = pagina.locator(seletor)

            try:
                if cartoes.count() > 0:
                    return cartoes

            except PlaywrightError:
                continue

        return pagina.locator(self.SELETORES_CARTAO[0])

    @staticmethod
    def _primeiro_texto(
        raiz,
        seletores: tuple[str, ...],
    ) -> str:
        for seletor in seletores:
            try:
                elemento = raiz.locator(seletor).first

                if elemento.count() == 0:
                    continue

                texto = elemento.inner_text(
                    timeout=2500,
                ).strip()

                if texto:
                    return texto

            except Exception:
                continue

        return ""

    @staticmethod
    def _primeiro_atributo(
        raiz,
        seletores: tuple[str, ...],
        atributo: str,
    ) -> str:
        for seletor in seletores:
            try:
                elemento = raiz.locator(seletor).first

                if elemento.count() == 0:
                    continue

                valor = elemento.get_attribute(
                    atributo,
                )

                if valor:
                    return str(valor).strip()

            except Exception:
                continue

        return ""

    def _pagina_possui_bloqueio(
        self,
        pagina: Page,
    ) -> bool:
        try:
            titulo = pagina.title().casefold()

            corpo = (
                pagina.locator("body")
                .inner_text(
                    timeout=5000,
                )
                .casefold()
            )

        except PlaywrightError:
            return False

        texto = titulo + "\n" + corpo[:5000]

        return any(indicador.casefold() in texto for indicador in self.INDICADORES_BLOQUEIO)
