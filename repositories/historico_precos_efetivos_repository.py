from __future__ import annotations

import json
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any


class HistoricoPrecosEfetivosRepository:
    def __init__(
        self,
        caminho_arquivo: str | Path,
        limite_registros_por_serie: int = 180,
    ) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)
        self.limite_registros_por_serie = limite_registros_por_serie
        self._dados = self._carregar()

    def _carregar(self) -> dict[str, Any]:
        if not self.caminho_arquivo.exists():
            return {
                "versao": 1,
                "atualizado_em": None,
                "series": {},
            }

        try:
            with self.caminho_arquivo.open(
                "r",
                encoding="utf-8",
            ) as arquivo:
                dados = json.load(arquivo)

            if not isinstance(dados, dict):
                raise ValueError("Historico efetivo precisa ser objeto JSON.")

            dados.setdefault("versao", 1)
            dados.setdefault(
                "atualizado_em",
                None,
            )
            dados.setdefault(
                "series",
                {},
            )

            return dados

        except (
            json.JSONDecodeError,
            OSError,
            ValueError,
        ) as erro:
            raise RuntimeError(
                "Nao foi possivel carregar historico " f"de precos efetivos: {erro}"
            ) from erro

    def salvar(self) -> None:
        self.caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._dados["atualizado_em"] = (
            datetime.now()
            .astimezone()
            .isoformat(
                timespec="seconds",
            )
        )

        temporario = self.caminho_arquivo.with_suffix(".tmp")

        with temporario.open(
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
            temporario,
            self.caminho_arquivo,
        )

    def obter_registros(
        self,
        chave_serie: str,
    ) -> list[dict[str, Any]]:
        serie = self._dados["series"].get(
            chave_serie,
            {},
        )

        registros = serie.get(
            "registros",
            [],
        )

        if not isinstance(
            registros,
            list,
        ):
            return []

        return deepcopy(registros)

    def registrar_preco_efetivo(
        self,
        *,
        chave_serie: str,
        chave_produto: str,
        marketplace: str,
        tipo_condicao: str,
        preco_efetivo: float,
        preco_oficial: float,
        coletado_em: str,
        fonte: str,
        codigo_cupom_observado: str | None,
        codigo_cupom_validado: bool,
    ) -> bool:
        series = self._dados["series"]

        serie = series.setdefault(
            chave_serie,
            {
                "chave": chave_serie,
                "chave_produto": (chave_produto),
                "marketplace": marketplace,
                "tipo_condicao": (tipo_condicao),
                "primeiro_registro_em": (coletado_em),
                "ultimo_registro_em": (coletado_em),
                "registros": [],
            },
        )

        serie["ultimo_registro_em"] = coletado_em

        registros = serie.setdefault(
            "registros",
            [],
        )

        novo = {
            "preco_efetivo": round(
                float(preco_efetivo),
                2,
            ),
            "preco_oficial": round(
                float(preco_oficial),
                2,
            ),
            "coletado_em": coletado_em,
            "fonte": fonte,
            "codigo_cupom_observado": (codigo_cupom_observado),
            "codigo_cupom_validado": bool(codigo_cupom_validado),
        }

        data_atual = self._extrair_data(coletado_em)

        for indice, registro in enumerate(registros):
            if self._extrair_data(str(registro.get("coletado_em") or "")) != data_atual:
                continue

            mudou = registro != novo

            registros[indice] = novo

            return mudou

        registros.append(novo)

        registros.sort(key=lambda registro: str(registro.get("coletado_em") or ""))

        if len(registros) > self.limite_registros_por_serie:
            serie["registros"] = registros[-self.limite_registros_por_serie :]

        return True

    def quantidade_series(self) -> int:
        return len(
            self._dados.get(
                "series",
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
