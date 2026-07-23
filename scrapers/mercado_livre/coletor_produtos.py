from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Locator, Page

from scrapers.mercado_livre.parser import (
    criar_chave_unica,
    montar_produto,
)


SELETOR_CARD = "li.poly-card"
SELETOR_TITULO = ".poly-component__title"
SELETOR_PRECO_ATUAL = ".poly-price__current"

SELETORES_PRECO_ANTERIOR = (
    ".andes-money-amount--previous",
    ".poly-price__original",
    ".poly-component__price--original",
    ".poly-price__previous",
    "s",
    "del",
)

SELETORES_DESCONTO = (
    ".andes-money-amount__discount",
    ".poly-price__discount",
    ".poly-component__discount",
    "[class*='discount']",
)

PASTA_RAIZ = Path(__file__).resolve().parents[2]

PASTA_DADOS_BRUTOS = (
    PASTA_RAIZ
    / "data"
    / "bruto"
)


class ColetorProdutosMercadoLivre:
    def __init__(
        self,
        pagina: Page,
        categoria: str | None = None,
        tempo_espera_scroll: float = 2.0,
        tentativas_sem_crescimento: int = 5,
        limite_scrolls: int = 150,
    ) -> None:
        self.pagina = pagina
        self.categoria = (
            categoria
            or "Não informada"
        )

        self.tempo_espera_scroll = (
            tempo_espera_scroll
        )

        self.tentativas_sem_crescimento = (
            tentativas_sem_crescimento
        )

        self.limite_scrolls = limite_scrolls

    def coletar(
        self,
    ) -> list[dict[str, Any]]:
        print(
            f"\nCategoria: {self.categoria}"
        )

        print(
            "Iniciando coleta e "
            "scroll automático...\n"
        )

        produtos_por_chave: dict[
            str,
            dict[str, Any],
        ] = {}

        quantidade_anterior = 0
        ciclos_sem_crescimento = 0

        for numero_scroll in range(
            1,
            self.limite_scrolls + 1,
        ):
            self._coletar_cards_visiveis(
                produtos_por_chave
            )

            quantidade_atual = len(
                produtos_por_chave
            )

            print(
                f"Scroll {numero_scroll:03d} | "
                f"Produtos únicos: "
                f"{quantidade_atual}"
            )

            if quantidade_atual > quantidade_anterior:
                ciclos_sem_crescimento = 0
                quantidade_anterior = (
                    quantidade_atual
                )
            else:
                ciclos_sem_crescimento += 1

            if (
                ciclos_sem_crescimento
                >= self.tentativas_sem_crescimento
            ):
                print(
                    "\nNenhum produto novo "
                    "apareceu após "
                    f"{self.tentativas_sem_crescimento} "
                    "tentativas."
                )
                break

            self._rolar_pagina()

            time.sleep(
                self.tempo_espera_scroll
            )

        produtos = list(
            produtos_por_chave.values()
        )

        print(
            "\nColeta encerrada: "
            f"{len(produtos)} "
            "produtos únicos."
        )

        return produtos

    def _coletar_cards_visiveis(
        self,
        produtos_por_chave: dict[
            str,
            dict[str, Any],
        ],
    ) -> None:
        cards = self.pagina.locator(
            SELETOR_CARD
        )

        quantidade_cards = cards.count()

        for indice in range(
            quantidade_cards
        ):
            card = cards.nth(indice)

            try:
                produto = (
                    self._extrair_produto_do_card(
                        card
                    )
                )

                if not produto:
                    continue

                chave = criar_chave_unica(
                    produto
                )

                if not chave:
                    continue

                produtos_por_chave[
                    chave
                ] = produto

            except Exception as erro:
                print(
                    "Aviso: não foi possível "
                    f"ler o card {indice + 1}: "
                    f"{erro}"
                )

    def _extrair_produto_do_card(
        self,
        card: Locator,
    ) -> dict[str, Any] | None:
        titulo_locator = card.locator(
            SELETOR_TITULO
        ).first

        if titulo_locator.count() == 0:
            return None

        titulo = titulo_locator.inner_text(
            timeout=3000
        ).strip()

        link = (
            titulo_locator.get_attribute(
                "href"
            )
            or ""
        )

        preco_texto = (
            self._extrair_texto_primeiro_seletor(
                card=card,
                seletores=(
                    SELETOR_PRECO_ATUAL,
                ),
            )
        )

        preco_anterior_texto = (
            self._extrair_texto_primeiro_seletor(
                card=card,
                seletores=(
                    SELETORES_PRECO_ANTERIOR
                ),
            )
        )

        desconto_texto = (
            self._extrair_texto_primeiro_seletor(
                card=card,
                seletores=(
                    SELETORES_DESCONTO
                ),
            )
        )

        texto_card = self._extrair_texto_card(
            card
        )

        imagem = self._extrair_imagem(
            card
        )

        if not titulo or not link:
            return None

        return montar_produto(
            titulo=titulo,
            preco_texto=preco_texto,
            preco_anterior_texto=(
                preco_anterior_texto
            ),
            desconto_texto=desconto_texto,
            texto_card=texto_card,
            link=link,
            imagem=imagem,
            categoria=self.categoria,
        )

    @staticmethod
    def _extrair_texto_primeiro_seletor(
        card: Locator,
        seletores: tuple[str, ...],
    ) -> str:
        for seletor in seletores:
            try:
                localizador = card.locator(
                    seletor
                ).first

                if localizador.count() == 0:
                    continue

                texto = localizador.inner_text(
                    timeout=1500
                ).strip()

                if texto:
                    return texto

            except Exception:
                continue

        return ""

    @staticmethod
    def _extrair_texto_card(
        card: Locator,
    ) -> str:
        try:
            return card.inner_text(
                timeout=3000
            ).strip()
        except Exception:
            return ""

    @staticmethod
    def _extrair_imagem(
        card: Locator,
    ) -> str:
        imagem_locator = card.locator(
            "img"
        ).first

        if imagem_locator.count() == 0:
            return ""

        atributos = (
            "src",
            "data-src",
            "data-lazy",
            "srcset",
        )

        for atributo in atributos:
            valor = (
                imagem_locator.get_attribute(
                    atributo
                )
            )

            if not valor:
                continue

            if atributo == "srcset":
                primeiro_item = (
                    valor
                    .split(",")[0]
                    .strip()
                )

                return (
                    primeiro_item
                    .split(" ")[0]
                    .strip()
                )

            return valor.strip()

        return ""

    def _rolar_pagina(self) -> None:
        self.pagina.evaluate(
            """
            () => {
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: "smooth"
                });
            }
            """
        )

    @staticmethod
    def salvar_json(
        produtos: list[dict[str, Any]],
        nome_arquivo: str,
    ) -> Path:
        caminho_arquivo = (
            PASTA_DADOS_BRUTOS
            / nome_arquivo
        )

        caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with caminho_arquivo.open(
            "w",
            encoding="utf-8",
        ) as arquivo:
            json.dump(
                produtos,
                arquivo,
                ensure_ascii=False,
                indent=4,
            )

        print(
            "\nArquivo salvo em:"
            f"\n{caminho_arquivo}"
        )

        return caminho_arquivo