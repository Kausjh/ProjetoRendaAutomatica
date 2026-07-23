from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PASTA_RAIZ = Path(__file__).resolve().parents[1]

PASTA_MERCADO_LIVRE = (
    PASTA_RAIZ
    / "data"
    / "bruto"
    / "mercado_livre"
)


class CarregadorProdutos:
    def __init__(
        self,
        pasta_origem: Path = PASTA_MERCADO_LIVRE,
    ) -> None:
        self.pasta_origem = pasta_origem

    def carregar_todos(
        self,
    ) -> tuple[list[dict[str, Any]], dict[str, int]]:
        if not self.pasta_origem.exists():
            raise FileNotFoundError(
                "A pasta de produtos não existe:\n"
                f"{self.pasta_origem}"
            )

        arquivos = sorted(
            self.pasta_origem.glob("*.json")
        )

        if not arquivos:
            raise FileNotFoundError(
                "Nenhum arquivo JSON foi encontrado em:\n"
                f"{self.pasta_origem}"
            )

        produtos_unicos: dict[
            str,
            dict[str, Any],
        ] = {}

        resumo_arquivos: dict[str, int] = {}

        for caminho_arquivo in arquivos:
            produtos = self._carregar_arquivo(
                caminho_arquivo
            )

            resumo_arquivos[
                caminho_arquivo.name
            ] = len(produtos)

            for produto in produtos:
                chave = self._criar_chave_produto(
                    produto
                )

                if not chave:
                    continue

                produtos_unicos[chave] = produto

        return (
            list(produtos_unicos.values()),
            resumo_arquivos,
        )

    @staticmethod
    def _carregar_arquivo(
        caminho_arquivo: Path,
    ) -> list[dict[str, Any]]:
        try:
            with caminho_arquivo.open(
                "r",
                encoding="utf-8",
            ) as arquivo:
                conteudo = json.load(arquivo)

        except json.JSONDecodeError as erro:
            raise ValueError(
                "JSON inválido no arquivo:\n"
                f"{caminho_arquivo}"
            ) from erro

        if not isinstance(conteudo, list):
            raise ValueError(
                "O conteúdo precisa ser uma lista "
                "de produtos:\n"
                f"{caminho_arquivo}"
            )

        return [
            item
            for item in conteudo
            if isinstance(item, dict)
        ]

    @staticmethod
    def _criar_chave_produto(
        produto: dict[str, Any],
    ) -> str:
        link = str(
            produto.get("link")
            or produto.get("url")
            or ""
        ).strip()

        if link:
            link = link.split("?")[0]
            return f"link:{link.lower()}"

        produto_id = str(
            produto.get("id")
            or produto.get("produto_id")
            or produto.get("id_produto")
            or ""
        ).strip()

        if produto_id:
            return f"id:{produto_id.lower()}"

        titulo = str(
            produto.get("titulo")
            or produto.get("title")
            or produto.get("nome")
            or ""
        ).strip()

        preco = str(
            produto.get("preco")
            or produto.get("price")
            or ""
        ).strip()

        if titulo:
            return (
                f"titulo:{titulo.lower()}|"
                f"preco:{preco}"
            )

        return ""