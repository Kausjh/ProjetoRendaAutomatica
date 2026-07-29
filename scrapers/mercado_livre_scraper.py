import logging
import re
import time
from urllib.parse import quote_plus

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Page,
    sync_playwright,
)
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from models.oferta import Oferta
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class MercadoLivreScraper(BaseScraper):
    """
    Coleta produtos diretamente das páginas de busca do Mercado Livre.

    O scraper conecta ao Chrome já aberto através do Chrome DevTools
    Protocol, utilizando a porta 9222.
    """

    ENDPOINT_CDP = "http://127.0.0.1:9222"

    URL_BUSCA = "https://lista.mercadolivre.com.br/{termo}"

    SELETORES_CARTAO = [
        "li.ui-search-layout__item",
        "div.ui-search-result__wrapper",
        "div.poly-card",
    ]

    TERMOS_PADRAO = [
        "Ryzen 5",
        "Ryzen 7",
        "Intel Core i5",
        "Intel Core i7",
        "RTX placa de vídeo",
        "RX placa de vídeo",
        "SSD NVMe",
        "Memória RAM DDR4",
        "Memória RAM DDR5",
        "Monitor gamer",
        "Fonte Corsair",
        "Fonte MSI",
        "Placa mãe B550",
        "Placa mãe B650",
        "Gabinete gamer",
        "Mouse Logitech",
        "Teclado Redragon",
        "Headset HyperX",
    ]

    def __init__(
        self,
        termos_busca: list[str] | None = None,
        endpoint_cdp: str | None = None,
    ) -> None:
        termos_recebidos = termos_busca if termos_busca is not None else self.TERMOS_PADRAO

        self.termos_busca = [termo.strip() for termo in termos_recebidos if termo and termo.strip()]

        if not self.termos_busca:
            raise ValueError("A lista de termos do Mercado Livre não pode estar vazia.")

        self.endpoint_cdp = endpoint_cdp.strip() if endpoint_cdp else self.ENDPOINT_CDP

    def buscar_ofertas(
        self,
        limite: int = 5,
    ) -> list[Oferta]:
        if limite <= 0:
            logger.warning(
                "Limite inválido para o Mercado Livre: %s.",
                limite,
            )
            return []

        logger.info(
            "Conectando ao Chrome pelo CDP em %s.",
            self.endpoint_cdp,
        )

        ofertas: list[Oferta] = []
        chaves_processadas: set[str] = set()

        try:
            with sync_playwright() as playwright:
                navegador = playwright.chromium.connect_over_cdp(
                    self.endpoint_cdp,
                    timeout=30000,
                )

                contexto = self._obter_contexto(navegador)

                pagina = contexto.new_page()

                pagina.set_default_timeout(15000)

                try:
                    for indice, termo in enumerate(
                        self.termos_busca,
                        start=1,
                    ):
                        logger.info(
                            "Pesquisando no Mercado Livre " "(%s/%s): %s",
                            indice,
                            len(self.termos_busca),
                            termo,
                        )

                        ofertas_termo = self._buscar_termo(
                            pagina=pagina,
                            termo=termo,
                            limite=limite,
                        )

                        adicionadas = 0

                        for oferta in ofertas_termo:
                            chave = self._criar_chave_oferta(oferta)

                            if chave in chaves_processadas:
                                continue

                            chaves_processadas.add(chave)

                            ofertas.append(oferta)

                            adicionadas += 1

                        logger.info(
                            "Termo '%s': %s oferta(s) " "válida(s), %s nova(s).",
                            termo,
                            len(ofertas_termo),
                            adicionadas,
                        )

                        time.sleep(1.5)

                finally:
                    if not pagina.is_closed():
                        pagina.close()

                navegador.close()

        except PlaywrightError as erro:
            logger.exception(
                "Não foi possível usar o Chrome pelo CDP. "
                "Confirme se ele está aberto com a porta 9222. "
                "Detalhes: %s",
                erro,
            )

            return []

        logger.info(
            "Mercado Livre: %s oferta(s) única(s) coletada(s).",
            len(ofertas),
        )

        return ofertas

    def _obter_contexto(
        self,
        navegador: Browser,
    ) -> BrowserContext:
        if navegador.contexts:
            return navegador.contexts[0]

        logger.warning(
            "Nenhum contexto existente foi encontrado no Chrome. " "Criando um novo contexto."
        )

        return navegador.new_context(
            locale="pt-BR",
        )

    def _buscar_termo(
        self,
        pagina: Page,
        termo: str,
        limite: int,
    ) -> list[Oferta]:
        termo_url = quote_plus(termo).replace(
            "+",
            "-",
        )

        url = self.URL_BUSCA.format(termo=termo_url)

        try:
            pagina.goto(
                url,
                wait_until="domcontentloaded",
                timeout=45000,
            )

            pagina.wait_for_load_state(
                "domcontentloaded",
                timeout=15000,
            )

        except PlaywrightTimeoutError:
            logger.warning(
                "Tempo esgotado durante a navegação " "da busca '%s'. Continuando a tentativa.",
                termo,
            )

        except PlaywrightError as erro:
            logger.warning(
                "Erro ao abrir a busca '%s': %s",
                termo,
                erro,
            )

            return []

        if self._pagina_possui_bloqueio(pagina):
            logger.warning(
                "O Mercado Livre exibiu uma verificação " "ou bloqueio para o termo '%s'.",
                termo,
            )

            return []

        carregou_produtos = self._aguardar_produtos(
            pagina=pagina,
            termo=termo,
        )

        if not carregou_produtos:
            if self._pagina_possui_bloqueio(pagina):
                logger.warning(
                    "O Mercado Livre exibiu uma verificação "
                    "ou bloqueio após carregar o termo '%s'.",
                    termo,
                )

            return []

        cartoes = self._obter_cartoes(pagina)

        quantidade_cartoes = cartoes.count()

        if quantidade_cartoes == 0:
            logger.warning(
                "Nenhum cartão de produto encontrado " "para o termo '%s'.",
                termo,
            )

            return []

        logger.debug(
            "Busca '%s': %s cartão(ões) localizado(s).",
            termo,
            quantidade_cartoes,
        )

        quantidade_analisar = min(
            quantidade_cartoes,
            limite,
        )

        ofertas: list[Oferta] = []

        for indice in range(quantidade_analisar):
            cartao = cartoes.nth(indice)

            try:
                oferta = self._extrair_oferta(cartao)

                if oferta is not None:
                    ofertas.append(oferta)

            except Exception:
                logger.exception(
                    "Erro ao processar o produto %s " "da busca '%s'.",
                    indice + 1,
                    termo,
                )

        return ofertas

    def _aguardar_produtos(
        self,
        pagina: Page,
        termo: str,
    ) -> bool:
        seletor_principal = self.SELETORES_CARTAO[0]

        try:
            pagina.wait_for_selector(
                seletor_principal,
                state="attached",
                timeout=15000,
            )

            pagina.wait_for_timeout(1000)

            return True

        except PlaywrightTimeoutError:
            logger.warning(
                "Os cartões principais da busca '%s' " "não apareceram em 15 segundos.",
                termo,
            )

        for seletor_alternativo in self.SELETORES_CARTAO[1:]:
            try:
                pagina.wait_for_selector(
                    seletor_alternativo,
                    state="attached",
                    timeout=5000,
                )

                pagina.wait_for_timeout(1000)

                logger.info(
                    "A busca '%s' carregou usando o " "seletor alternativo '%s'.",
                    termo,
                    seletor_alternativo,
                )

                return True

            except PlaywrightTimeoutError:
                continue

            except PlaywrightError as erro:
                logger.debug(
                    "Erro ao testar o seletor '%s' " "na busca '%s': %s",
                    seletor_alternativo,
                    termo,
                    erro,
                )

        try:
            pagina.mouse.wheel(
                0,
                800,
            )

            pagina.wait_for_timeout(3000)

            pagina.mouse.wheel(
                0,
                -800,
            )

            pagina.wait_for_timeout(1000)

        except PlaywrightError:
            pass

        for seletor in self.SELETORES_CARTAO:
            try:
                quantidade = pagina.locator(seletor).count()

                if quantidade > 0:
                    logger.info(
                        "A busca '%s' carregou após a " "tentativa adicional. Seletor: %s.",
                        termo,
                        seletor,
                    )

                    return True

            except PlaywrightError:
                continue

        logger.warning(
            "Nenhum cartão de produto foi renderizado " "para o termo '%s'.",
            termo,
        )

        return False

    def _obter_cartoes(
        self,
        pagina: Page,
    ):
        for seletor in self.SELETORES_CARTAO:
            cartoes = pagina.locator(seletor)

            try:
                quantidade = cartoes.count()

            except PlaywrightError:
                continue

            if quantidade > 0:
                logger.debug(
                    "Seletor de cartões utilizado: %s.",
                    seletor,
                )

                return cartoes

        return pagina.locator(self.SELETORES_CARTAO[0])

    def _extrair_oferta(
        self,
        cartao,
    ) -> Oferta | None:
        nome = self._primeiro_texto(
            cartao,
            [
                "a.poly-component__title",
                "h3.poly-component__title-wrapper",
                "h2.ui-search-item__title",
                ".ui-search-item__title",
            ],
        )

        link = self._primeiro_atributo(
            cartao,
            [
                "a.poly-component__title",
                "h3.poly-component__title-wrapper a",
                "a.ui-search-item__group__element",
                "a[href*='produto.mercadolivre.com.br']",
                "a[href*='mercadolivre.com.br']",
            ],
            "href",
        )

        imagem = self._primeiro_atributo(
            cartao,
            [
                "img.poly-component__picture",
                "img.ui-search-result-image__element",
                "img[data-testid='picture']",
                "img",
            ],
            "src",
        )

        if not imagem:
            imagem = self._primeiro_atributo(
                cartao,
                [
                    "img.poly-component__picture",
                    "img.ui-search-result-image__element",
                    "img[data-testid='picture']",
                    "img",
                ],
                "data-src",
            )

        if not imagem:
            imagem = self._primeira_imagem_srcset(cartao)

        preco = self._extrair_preco_atual(cartao)

        preco_antigo = self._extrair_preco_antigo(cartao)

        if not nome or preco is None or not link:
            return None

        link = self._limpar_link(link)

        imagem = self._normalizar_imagem(imagem)

        return Oferta(
            nome=nome,
            loja="Mercado Livre",
            preco=preco,
            preco_antigo=preco_antigo,
            link=link,
            imagem=imagem,
            moeda="R$",
        )

    def _primeira_imagem_srcset(
        self,
        cartao,
    ) -> str | None:
        srcset = self._primeiro_atributo(
            cartao,
            [
                "img.poly-component__picture",
                "img.ui-search-result-image__element",
                "img[data-testid='picture']",
                "img",
            ],
            "srcset",
        )

        if not srcset:
            return None

        candidatos = [item.strip() for item in srcset.split(",") if item.strip()]

        if not candidatos:
            return None

        ultimo_candidato = candidatos[-1]

        return ultimo_candidato.split()[0].strip()

    def _extrair_preco_atual(
        self,
        cartao,
    ) -> float | None:
        seletores = [
            (".poly-price__current " ".andes-money-amount"),
            (".ui-search-price__second-line " ".andes-money-amount"),
            (".poly-component__price " ".andes-money-amount"),
            (".andes-money-amount"),
        ]

        for seletor in seletores:
            elementos = cartao.locator(seletor)

            quantidade = elementos.count()

            for indice in range(quantidade):
                elemento = elementos.nth(indice)

                valor = self._extrair_valor_money_amount(elemento)

                if valor is not None:
                    return valor

        return None

    def _extrair_preco_antigo(
        self,
        cartao,
    ) -> float | None:
        seletores = [
            (".andes-money-amount--previous"),
            (".andes-money-amount--previous " ".andes-money-amount"),
            (".ui-search-price__original-value"),
            (".ui-search-price__original-value " ".andes-money-amount"),
            ("s.andes-money-amount"),
            (".poly-price__previous " ".andes-money-amount"),
        ]

        for seletor in seletores:
            elementos = cartao.locator(seletor)

            quantidade = elementos.count()

            for indice in range(quantidade):
                valor = self._extrair_valor_money_amount(elementos.nth(indice))

                if valor is not None:
                    return valor

        return None

    def _extrair_valor_money_amount(
        self,
        elemento,
    ) -> float | None:
        texto_accessivel = elemento.get_attribute("aria-label")

        if texto_accessivel:
            valor = self._converter_preco(texto_accessivel)

            if valor is not None:
                return valor

        fracao = self._texto_opcional(elemento.locator(".andes-money-amount__fraction").first)

        centavos = self._texto_opcional(elemento.locator(".andes-money-amount__cents").first)

        if fracao:
            texto = fracao

            if centavos:
                texto += f",{centavos}"

            valor = self._converter_preco(texto)

            if valor is not None:
                return valor

        return self._converter_preco(self._texto_opcional(elemento))

    def _primeiro_texto(
        self,
        raiz,
        seletores: list[str],
    ) -> str | None:
        for seletor in seletores:
            elementos = raiz.locator(seletor)

            if elementos.count() == 0:
                continue

            texto = self._texto_opcional(elementos.first)

            if texto:
                return " ".join(texto.split())

        return None

    def _primeiro_atributo(
        self,
        raiz,
        seletores: list[str],
        atributo: str,
    ) -> str | None:
        for seletor in seletores:
            elementos = raiz.locator(seletor)

            if elementos.count() == 0:
                continue

            valor = elementos.first.get_attribute(atributo)

            if valor:
                return valor.strip()

        return None

    @staticmethod
    def _texto_opcional(
        elemento,
    ) -> str | None:
        try:
            if elemento.count() == 0:
                return None

            texto = elemento.inner_text(timeout=3000).strip()

            return texto or None

        except PlaywrightError:
            return None

    @staticmethod
    def _converter_preco(
        texto: str | None,
    ) -> float | None:
        if not texto:
            return None

        texto_normalizado = texto.lower()

        texto_normalizado = texto_normalizado.replace(
            "\xa0",
            " ",
        )

        texto_normalizado = texto_normalizado.replace(
            "reais",
            "",
        )

        texto_normalizado = texto_normalizado.replace(
            "real",
            "",
        )

        texto_normalizado = texto_normalizado.replace(
            "com",
            ",",
        )

        texto_normalizado = texto_normalizado.replace(
            "centavos",
            "",
        )

        texto_normalizado = texto_normalizado.replace(
            "centavo",
            "",
        )

        correspondencia = re.search(
            r"(\d[\d.\s]*)(?:[,.](\d{1,2}))?",
            texto_normalizado,
        )

        if not correspondencia:
            return None

        parte_inteira = correspondencia.group(1)

        parte_decimal = correspondencia.group(2)

        parte_inteira = re.sub(
            r"[^\d]",
            "",
            parte_inteira,
        )

        if not parte_inteira:
            return None

        valor = float(parte_inteira)

        if parte_decimal:
            valor += (
                int(
                    parte_decimal.ljust(
                        2,
                        "0",
                    )[:2]
                )
                / 100
            )

        return valor

    @staticmethod
    def _limpar_link(
        link: str,
    ) -> str:
        return link.split("#")[0].strip()

    @staticmethod
    def _normalizar_imagem(
        imagem: str | None,
    ) -> str | None:
        if not imagem:
            return None

        return imagem.replace(
            "http://",
            "https://",
        ).strip()

    @staticmethod
    def _criar_chave_oferta(
        oferta: Oferta,
    ) -> str:
        link = str(oferta.link).split("?")[0].rstrip("/").lower()

        if link:
            return link

        nome = re.sub(
            r"\s+",
            " ",
            oferta.nome.lower(),
        ).strip()

        return f"{oferta.loja.lower()}|" f"{nome}|" f"{oferta.preco:.2f}"

    @staticmethod
    def _pagina_possui_bloqueio(
        pagina: Page,
    ) -> bool:
        try:
            titulo = pagina.title().lower()

            conteudo = pagina.locator("body").inner_text(timeout=5000).lower()

        except PlaywrightError:
            return False

        indicadores = [
            "captcha",
            "não conseguimos confirmar",
            "verifique que você é humano",
            "atividade incomum",
            "acesso negado",
            "access denied",
        ]

        texto_completo = titulo + "\n" + conteudo[:5000]

        return any(indicador in texto_completo for indicador in indicadores)
