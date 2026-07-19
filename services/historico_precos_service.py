from dataclasses import dataclass

from models.oferta import Oferta
from repositories.historico_precos_repository import (
    HistoricoPrecosRepository
)


@dataclass
class ResultadoHistoricoPreco:
    primeiro_registro: bool
    preco_anterior: float | None
    menor_preco_anterior: float | None
    menor_preco_historico: bool
    variacao_percentual: float
    preco_caiu: bool
    preco_subiu: bool
    novo_preco_registrado: bool
    quantidade_registros: int


class HistoricoPrecosService:
    def __init__(
        self,
        repository: HistoricoPrecosRepository
    ) -> None:
        self.repository = repository

    def analisar_e_registrar(
        self,
        oferta: Oferta
    ) -> ResultadoHistoricoPreco:
        historico_anterior = self.repository.obter_historico(
            oferta.link
        )

        primeiro_registro = len(
            historico_anterior
        ) == 0

        preco_anterior = self._obter_preco_anterior(
            historico_anterior
        )

        menor_preco_anterior = self._obter_menor_preco(
            historico_anterior
        )

        variacao_percentual = self._calcular_variacao_percentual(
            preco_anterior=preco_anterior,
            preco_atual=oferta.preco
        )

        preco_caiu = (
            preco_anterior is not None
            and oferta.preco < preco_anterior
        )

        preco_subiu = (
            preco_anterior is not None
            and oferta.preco > preco_anterior
        )

        menor_preco_historico = self._verificar_menor_preco_historico(
            preco_atual=oferta.preco,
            menor_preco_anterior=menor_preco_anterior
        )

        novo_preco_registrado = self.repository.registrar_preco(
            oferta
        )

        quantidade_registros = len(
            historico_anterior
        )

        if novo_preco_registrado:
            quantidade_registros += 1

        return ResultadoHistoricoPreco(
            primeiro_registro=primeiro_registro,
            preco_anterior=preco_anterior,
            menor_preco_anterior=menor_preco_anterior,
            menor_preco_historico=menor_preco_historico,
            variacao_percentual=variacao_percentual,
            preco_caiu=preco_caiu,
            preco_subiu=preco_subiu,
            novo_preco_registrado=novo_preco_registrado,
            quantidade_registros=quantidade_registros
        )

    def _obter_preco_anterior(
        self,
        historico: list[dict]
    ) -> float | None:
        if not historico:
            return None

        ultimo_registro = historico[-1]

        preco = ultimo_registro.get(
            "preco"
        )

        if not isinstance(
            preco,
            int | float
        ):
            return None

        return float(
            preco
        )

    def _obter_menor_preco(
        self,
        historico: list[dict]
    ) -> float | None:
        precos_validos = []

        for registro in historico:
            preco = registro.get(
                "preco"
            )

            if isinstance(
                preco,
                int | float
            ):
                precos_validos.append(
                    float(preco)
                )

        if not precos_validos:
            return None

        return min(
            precos_validos
        )

    def _verificar_menor_preco_historico(
        self,
        preco_atual: float,
        menor_preco_anterior: float | None
    ) -> bool:
        if menor_preco_anterior is None:
            return True

        return preco_atual < menor_preco_anterior

    def _calcular_variacao_percentual(
        self,
        preco_anterior: float | None,
        preco_atual: float
    ) -> float:
        if preco_anterior is None:
            return 0.0

        if preco_anterior <= 0:
            return 0.0

        variacao = (
            (preco_atual - preco_anterior)
            / preco_anterior
        ) * 100

        return round(
            variacao,
            2
        )