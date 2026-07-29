from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


class HistoricoPrecosRepository:
    def __init__(
        self,
        caminho_arquivo: str | Path,
        limite_registros_por_produto: int = 180,
    ) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)

        self.limite_registros_por_produto = limite_registros_por_produto

        self._dados = self._carregar()

    def _carregar(self) -> dict[str, Any]:
        if not self.caminho_arquivo.exists():
            return {
                "versao": 1,
                "atualizado_em": None,
                "produtos": {},
            }

        try:
            with self.caminho_arquivo.open(
                "r",
                encoding="utf-8",
            ) as arquivo:
                dados = json.load(arquivo)

            if not isinstance(dados, dict):
                raise ValueError("O histórico precisa ser um objeto JSON.")

            dados.setdefault("versao", 1)
            dados.setdefault("atualizado_em", None)
            dados.setdefault("produtos", {})

            return dados

        except (
            json.JSONDecodeError,
            OSError,
            ValueError,
        ) as erro:
            raise RuntimeError(
                "Não foi possível carregar o histórico "
                f"de preços em {self.caminho_arquivo}: {erro}"
            ) from erro

    def salvar(self) -> None:
        self.caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._dados["atualizado_em"] = datetime.now().astimezone().isoformat(timespec="seconds")

        caminho_temporario = self.caminho_arquivo.with_suffix(".tmp")

        with caminho_temporario.open(
            "w",
            encoding="utf-8",
        ) as arquivo:
            json.dump(
                self._dados,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(
            caminho_temporario,
            self.caminho_arquivo,
        )

    def obter_produto(
        self,
        chave_produto: str,
    ) -> dict[str, Any] | None:
        produto = self._dados["produtos"].get(chave_produto)

        if produto is None:
            return None

        return deepcopy(produto)

    def obter_registros(
        self,
        chave_produto: str,
    ) -> list[dict[str, Any]]:
        produto = self._dados["produtos"].get(
            chave_produto,
            {},
        )

        registros = produto.get(
            "registros",
            [],
        )

        if not isinstance(registros, list):
            return []

        return deepcopy(registros)

    def registrar_preco(
        self,
        chave_produto: str,
        titulo: str,
        link: str,
        categoria: str,
        preco: float,
        coletado_em: str,
    ) -> bool:
        produtos = self._dados["produtos"]

        produto = produtos.setdefault(
            chave_produto,
            {
                "chave": chave_produto,
                "titulo": titulo,
                "link": link,
                "categoria": categoria,
                "primeiro_registro_em": coletado_em,
                "ultimo_registro_em": coletado_em,
                "registros": [],
            },
        )

        produto["titulo"] = titulo
        produto["link"] = link
        produto["categoria"] = categoria
        produto["ultimo_registro_em"] = coletado_em

        registros = produto.setdefault(
            "registros",
            [],
        )

        data_atual = self._extrair_data(coletado_em)

        for registro in registros:
            data_registro = self._extrair_data(str(registro.get("coletado_em") or ""))

            if data_registro != data_atual:
                continue

            preco_existente = self._converter_float(registro.get("preco"))

            registro["preco"] = round(
                preco,
                2,
            )

            registro["coletado_em"] = coletado_em

            return preco_existente is None or round(preco_existente, 2) != round(preco, 2)

        registros.append(
            {
                "preco": round(preco, 2),
                "coletado_em": coletado_em,
            }
        )

        registros.sort(key=lambda registro: str(registro.get("coletado_em") or ""))

        if len(registros) > self.limite_registros_por_produto:
            produto["registros"] = registros[-self.limite_registros_por_produto :]

        return True

    def quantidade_produtos(self) -> int:
        return len(
            self._dados.get(
                "produtos",
                {},
            )
        )

    @staticmethod
    def _extrair_data(
        data_hora: str,
    ) -> str:
        if not data_hora:
            return ""

        return data_hora[:10]

    @staticmethod
    def _converter_float(
        valor: Any,
    ) -> float | None:
        if valor is None:
            return None

        if isinstance(valor, bool):
            return None

        if isinstance(valor, (int, float)):
            return float(valor)

        try:
            return float(
                str(valor).replace(
                    ",",
                    ".",
                )
            )

        except ValueError:
            return None
