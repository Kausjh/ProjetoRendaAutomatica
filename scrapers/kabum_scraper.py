# 63.8738, -149.7525

import logging
import re
import time
from typing import Any
from urllib.parse import quote

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Locator,
    Page,
    sync_playwright,
)
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from models.oferta import Oferta
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class KabumScraper(BaseScraper):
    """
    Coleta ofertas das páginas de busca da KaBuM!.

    Utiliza uma instância do Chrome aberta com o Chrome
    DevTools Protocol na porta 9222.
    """

    ENDPOINT_CDP = "http://127.0.0.1:9222"

    URL_BASE = "https://www.kabum.com.br"
    URL_BUSCA = f"{URL_BASE}/busca/{{termo}}"

    SELETOR_CARTAO = 'a[href^="/produto/"]'

    TERMOS_PADRAO = [
        "Ryzen 5",
        "Ryzen 7",
        "Intel Core i5",
        "Intel Core i7",
        "RTX placa de video",
        "RX placa de video",
        "SSD NVMe",
        "Memoria RAM DDR4",
        "Memoria RAM DDR5",
        "Monitor gamer",
        "Fonte Corsair",
        "Fonte MSI",
        "Placa mae B550",
        "Placa mae B650",
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
        termos = termos_busca if termos_busca is not None else self.TERMOS_PADRAO

        self.termos_busca = [termo.strip() for termo in termos if termo and termo.strip()]

        if not self.termos_busca:
            raise ValueError("A lista de termos da KaBuM! não pode estar vazia.")

        self.endpoint_cdp = endpoint_cdp.strip() if endpoint_cdp else self.ENDPOINT_CDP

    def buscar_ofertas(
        self,
        limite: int = 5,
    ) -> list[Oferta]:
        """
        Pesquisa todos os termos configurados.

        O limite é aplicado individualmente a cada termo.
        """

        if limite <= 0:
            logger.warning("O limite da KaBuM! deve ser maior que zero.")
            return []

        ofertas: list[Oferta] = []
        chaves_processadas: set[str] = set()

        logger.info(
            "Conectando ao Chrome pelo CDP em %s.",
            self.endpoint_cdp,
        )

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
                            "Pesquisando na KaBuM! (%s/%s): %s",
                            indice,
                            len(self.termos_busca),
                            termo,
                        )

                        ofertas_do_termo = self._buscar_termo(
                            pagina=pagina,
                            termo=termo,
                            limite=limite,
                        )

                        novas = self._adicionar_ofertas_unicas(
                            destino=ofertas,
                            candidatas=ofertas_do_termo,
                            chaves_processadas=chaves_processadas,
                        )

                        logger.info(
                            "Termo '%s': %s oferta(s), " "%s nova(s).",
                            termo,
                            len(ofertas_do_termo),
                            novas,
                        )

                        time.sleep(1.5)

                finally:
                    if not pagina.is_closed():
                        pagina.close()

                navegador.close()

        except PlaywrightError as erro:
            logger.error(
                "Não foi possível acessar o Chrome pela porta " "9222: %s",
                erro,
            )
            return []

        logger.info(
            "KaBuM!: %s oferta(s) única(s) coletada(s).",
            len(ofertas),
        )

        return ofertas

    @staticmethod
    def _obter_contexto(
        navegador: Browser,
    ) -> BrowserContext:
        if navegador.contexts:
            return navegador.contexts[0]

        return navegador.new_context(
            locale="pt-BR",
        )

    def _buscar_termo(
        self,
        pagina: Page,
        termo: str,
        limite: int,
    ) -> list[Oferta]:
        url = self._montar_url_busca(termo)

        if not self._abrir_pagina_busca(
            pagina=pagina,
            url=url,
            termo=termo,
        ):
            return []

        if self._pagina_possui_bloqueio(pagina):
            logger.warning(
                "A KaBuM! apresentou uma verificação ou " "bloqueio na busca por '%s'.",
                termo,
            )
            return []

        if not self._aguardar_produtos(
            pagina=pagina,
            termo=termo,
        ):
            return []

        cartoes = pagina.locator(self.SELETOR_CARTAO)

        try:
            quantidade = cartoes.count()

        except PlaywrightError as erro:
            logger.warning(
                "Não foi possível contar os produtos de '%s': %s",
                termo,
                erro,
            )
            return []

        logger.info(
            "Busca '%s': %s cartão(ões) encontrado(s).",
            termo,
            quantidade,
        )

        return self._extrair_ofertas_dos_cartoes(
            cartoes=cartoes,
            quantidade=quantidade,
            limite=limite,
            termo=termo,
        )

    def _abrir_pagina_busca(
        self,
        pagina: Page,
        url: str,
        termo: str,
    ) -> bool:
        try:
            pagina.goto(
                url,
                wait_until="domcontentloaded",
                timeout=45000,
            )

            return True

        except PlaywrightTimeoutError:
            logger.warning(
                "A busca por '%s' demorou além do esperado. "
                "A página será verificada mesmo assim.",
                termo,
            )
            return True

        except PlaywrightError as erro:
            logger.warning(
                "Erro ao abrir a busca por '%s': %s",
                termo,
                erro,
            )
            return False

    def _aguardar_produtos(
        self,
        pagina: Page,
        termo: str,
    ) -> bool:
        try:
            pagina.wait_for_selector(
                self.SELETOR_CARTAO,
                state="attached",
                timeout=20000,
            )

            pagina.wait_for_timeout(1500)

            return True

        except PlaywrightTimeoutError:
            logger.warning(
                "Os produtos da busca '%s' não apareceram " "dentro do tempo esperado.",
                termo,
            )

        except PlaywrightError as erro:
            logger.warning(
                "Erro ao aguardar os produtos de '%s': %s",
                termo,
                erro,
            )
            return False

        return self._tentar_carregar_produtos_com_rolagem(pagina)

    def _tentar_carregar_produtos_com_rolagem(
        self,
        pagina: Page,
    ) -> bool:
        try:
            pagina.mouse.wheel(
                0,
                1200,
            )

            pagina.wait_for_timeout(3000)

            return pagina.locator(self.SELETOR_CARTAO).count() > 0

        except PlaywrightError:
            return False

    def _extrair_ofertas_dos_cartoes(
        self,
        cartoes: Locator,
        quantidade: int,
        limite: int,
        termo: str,
    ) -> list[Oferta]:
        ofertas: list[Oferta] = []
        chaves_locais: set[str] = set()

        for indice in range(quantidade):
            if len(ofertas) >= limite:
                break

            try:
                dados = self._capturar_dados_do_cartao(cartoes.nth(indice))

                oferta = self._criar_oferta(dados)

                if oferta is None:
                    continue

                chave = self._criar_chave_oferta(oferta)

                if chave in chaves_locais:
                    continue

                chaves_locais.add(chave)

                ofertas.append(oferta)

            except PlaywrightError as erro:
                logger.warning(
                    "Erro ao capturar o produto %s da busca " "'%s': %s",
                    indice + 1,
                    termo,
                    erro,
                )

            except Exception as erro:
                logger.warning(
                    "Erro ao processar o produto %s da busca " "'%s': %s",
                    indice + 1,
                    termo,
                    erro,
                )

        return ofertas

    @staticmethod
    def _capturar_dados_do_cartao(
        cartao: Locator,
    ) -> dict[str, Any]:
        """
        Captura todos os dados do card em uma única execução
        JavaScript.

        Isso evita misturar dados de produtos diferentes caso
        a página reorganize os cards durante a coleta.
        """

        return cartao.evaluate(
            """
            (card) => {
                const pegarTextos = (seletor) => {
                    return Array
                        .from(card.querySelectorAll(seletor))
                        .map((elemento) => {
                            return (elemento.innerText || "")
                                .replace(/\\s+/g, " ")
                                .trim();
                        })
                        .filter(Boolean);
                };

                const nomeExato = card.querySelector(
                    "span.text-sm.text-left.text-gray-800."
                    + "text-ellipsis.line-clamp-2"
                );

                const nomeAlternativo = card.querySelector(
                    "span.line-clamp-2"
                );

                const imagem = card.querySelector("img");

                return {
                    href: card.getAttribute("href"),
                    texto: (card.innerText || "").trim(),

                    nome: (
                        nomeExato?.innerText
                        || nomeAlternativo?.innerText
                        || ""
                    )
                        .replace(/\\s+/g, " ")
                        .trim(),

                    precosAtuais: pegarTextos(
                        "span.text-base.font-semibold.text-gray-800"
                    ),

                    precosAtuaisAlternativos: pegarTextos(
                        "span.font-semibold.text-gray-800"
                    ),

                    precosAntigos: pegarTextos(
                        "span.line-through"
                    ),

                    imagem: imagem
                        ? (
                            imagem.getAttribute("src")
                            || imagem.getAttribute("data-src")
                            || imagem.getAttribute("srcset")
                        )
                        : null,
                };
            }
            """
        )

    def _criar_oferta(
        self,
        dados: dict[str, Any],
    ) -> Oferta | None:
        nome = self._normalizar_texto(dados.get("nome"))

        link = dados.get("href")

        preco = self._extrair_preco_atual_dos_dados(dados)

        if not nome or not isinstance(link, str) or not link.strip() or preco is None:
            return None

        preco_antigo = self._extrair_preco_antigo_dos_dados(
            dados=dados,
            preco_atual=preco,
        )

        link_normalizado = self._normalizar_link(link)

        imagem = self._normalizar_imagem(dados.get("imagem"))

        return Oferta(
            nome=nome,
            loja="KaBuM!",
            preco=preco,
            preco_antigo=preco_antigo,
            link=link_normalizado,
            imagem=imagem,
            moeda="R$",
            marketplace="kabum",
            id_produto=self._extrair_id_produto(link_normalizado),
        )

    def _extrair_preco_atual_dos_dados(
        self,
        dados: dict[str, Any],
    ) -> float | None:
        grupos = [
            dados.get(
                "precosAtuais",
                [],
            ),
            dados.get(
                "precosAtuaisAlternativos",
                [],
            ),
        ]

        for grupo in grupos:
            if not isinstance(
                grupo,
                list,
            ):
                continue

            for texto in grupo:
                preco = self._converter_preco(texto)

                if preco is not None:
                    return preco

        texto_card = dados.get("texto")

        return self._extrair_preco_atual_do_texto(texto_card)

    def _extrair_preco_antigo_dos_dados(
        self,
        dados: dict[str, Any],
        preco_atual: float,
    ) -> float | None:
        """
        Aceita apenas valores presentes em elementos line-through.

        Nenhum preço antigo é reconstruído ou inventado.
        """

        textos = dados.get(
            "precosAntigos",
            [],
        )

        if not isinstance(
            textos,
            list,
        ):
            return None

        candidatos: list[float] = []

        for texto in textos:
            valor = self._converter_preco(texto)

            if valor is not None and valor > preco_atual:
                candidatos.append(valor)

        if not candidatos:
            return None

        return min(candidatos)

    def _extrair_preco_atual_do_texto(
        self,
        texto: str | None,
    ) -> float | None:
        """
        Estratégia reserva caso as classes CSS sejam alteradas.

        Procura o valor imediatamente anterior ao texto "No PIX".
        """

        if not texto:
            return None

        texto_normalizado = texto.replace(
            "\xa0",
            " ",
        )

        correspondencia = re.search(
            r"R\$\s*" r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})" r"\s*(?:Desconto.*?\s*)?" r"No PIX",
            texto_normalizado,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if correspondencia:
            return self._converter_preco(correspondencia.group(1))

        valores = re.findall(
            r"R\$\s*" r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
            texto_normalizado,
        )

        if not valores:
            return None

        return self._converter_preco(valores[-1])

    @staticmethod
    def _converter_preco(
        texto: str | None,
    ) -> float | None:
        if not texto:
            return None

        texto_normalizado = str(texto).replace("\xa0", " ").replace("R$", "").strip()

        correspondencia = re.search(
            r"(\d{1,3}(?:\.\d{3})*|\d+)" r"(?:,(\d{1,2}))?",
            texto_normalizado,
        )

        if not correspondencia:
            return None

        parte_inteira = correspondencia.group(1).replace(".", "")

        parte_decimal = correspondencia.group(2)

        try:
            valor = float(parte_inteira)

            if parte_decimal:
                centavos = parte_decimal.ljust(
                    2,
                    "0",
                )[:2]

                valor += int(centavos) / 100

        except ValueError:
            return None

        if valor <= 0:
            return None

        return round(
            valor,
            2,
        )

    @staticmethod
    def _normalizar_texto(
        texto: Any,
    ) -> str | None:
        if not isinstance(
            texto,
            str,
        ):
            return None

        texto = " ".join(texto.split())

        return texto or None

    @classmethod
    def _montar_url_busca(
        cls,
        termo: str,
    ) -> str:
        termo_url = quote(
            termo.strip(),
            safe="",
        )

        return cls.URL_BUSCA.format(termo=termo_url)

    @classmethod
    def _normalizar_link(
        cls,
        link: str,
    ) -> str:
        link = link.strip()

        if link.startswith("/"):
            link = cls.URL_BASE + link

        return link.split("#")[0].strip()

    @classmethod
    def _normalizar_imagem(
        cls,
        imagem: Any,
    ) -> str | None:
        if not isinstance(
            imagem,
            str,
        ):
            return None

        imagem = imagem.strip()

        if not imagem:
            return None

        if "," in imagem:
            imagem = imagem.split(",")[0].strip()

        if " " in imagem:
            imagem = imagem.split(" ")[0].strip()

        if imagem.startswith("data:image"):
            return None

        if imagem.startswith("//"):
            imagem = "https:" + imagem

        elif imagem.startswith("/"):
            imagem = cls.URL_BASE + imagem

        return imagem.replace(
            "http://",
            "https://",
        )

    @staticmethod
    def _extrair_id_produto(
        link: str,
    ) -> str | None:
        correspondencia = re.search(
            r"/produto/(\d+)",
            link,
        )

        if not correspondencia:
            return None

        return correspondencia.group(1)

    @staticmethod
    def _criar_chave_oferta(
        oferta: Oferta,
    ) -> str:
        link = oferta.link.split("?")[0].rstrip("/").lower()

        if link:
            return link

        nome = re.sub(
            r"\s+",
            " ",
            oferta.nome.lower(),
        ).strip()

        return f"{oferta.loja.lower()}|" f"{nome}|" f"{oferta.preco:.2f}"

    def _adicionar_ofertas_unicas(
        self,
        destino: list[Oferta],
        candidatas: list[Oferta],
        chaves_processadas: set[str],
    ) -> int:
        adicionadas = 0

        for oferta in candidatas:
            chave = self._criar_chave_oferta(oferta)

            if chave in chaves_processadas:
                continue

            chaves_processadas.add(chave)

            destino.append(oferta)

            adicionadas += 1

        return adicionadas

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
            "verifique que você é humano",
            "atividade incomum",
            "acesso negado",
            "access denied",
            "cloudflare",
        ]

        texto_verificado = titulo + "\n" + conteudo[:5000]

        return any(indicador in texto_verificado for indicador in indicadores)
