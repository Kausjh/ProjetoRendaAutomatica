from models.oferta import Oferta
from services.historico_precos_service import (
    ResultadoHistoricoPreco
)


class PontuadorOferta:

    PONTOS_MAXIMOS_NICHO = 25
    PONTOS_MAXIMOS_DESCONTO = 40
    PONTOS_MAXIMOS_PRECO = 20
    PONTOS_MAXIMOS_QUEDA_PRECO = 10
    PONTOS_MENOR_PRECO_HISTORICO = 5

    QUEDA_PERCENTUAL_PARA_PONTUACAO_MAXIMA = 20

    def __init__(
        self,
        preco_maximo: float
    ) -> None:
        if preco_maximo <= 0:
            raise ValueError(
                "O preço máximo precisa ser maior que zero."
            )

        self.preco_maximo = preco_maximo

    def calcular(
        self,
        oferta: Oferta,
        resultado_historico: (
            ResultadoHistoricoPreco | None
        ) = None
    ) -> float:
        pontos_nicho = self._calcular_pontos_nicho(
            oferta
        )

        pontos_desconto = self._calcular_pontos_desconto(
            oferta
        )

        pontos_preco = self._calcular_pontos_preco(
            oferta
        )

        pontos_historico = self._calcular_pontos_historico(
            resultado_historico
        )

        pontuacao_total = (
            pontos_nicho
            + pontos_desconto
            + pontos_preco
            + pontos_historico
        )

        return round(
            min(
                max(pontuacao_total, 0),
                100
            ),
            2
        )

    def _calcular_pontos_nicho(
        self,
        oferta: Oferta
    ) -> float:
        if not oferta.eh_nicho:
            return 0

        relevancia_limitada = min(
            max(oferta.relevancia_nicho, 0),
            100
        )

        proporcao_relevancia = (
            relevancia_limitada
            / 100
        )

        return (
            proporcao_relevancia
            * self.PONTOS_MAXIMOS_NICHO
        )

    def _calcular_pontos_desconto(
        self,
        oferta: Oferta
    ) -> float:
        desconto = oferta.desconto_percentual

        desconto_limitado = min(
            max(desconto, 0),
            self.PONTOS_MAXIMOS_DESCONTO
        )

        return desconto_limitado

    def _calcular_pontos_preco(
        self,
        oferta: Oferta
    ) -> float:
        if oferta.preco <= 0:
            return 0

        if oferta.preco >= self.preco_maximo:
            return 0

        proporcao_economia = (
            self.preco_maximo - oferta.preco
        ) / self.preco_maximo

        return (
            proporcao_economia
            * self.PONTOS_MAXIMOS_PRECO
        )

    def _calcular_pontos_historico(
        self,
        resultado_historico: (
            ResultadoHistoricoPreco | None
        )
    ) -> float:
        if resultado_historico is None:
            return 0

        if resultado_historico.primeiro_registro:
            return 0

        pontos_queda = self._calcular_pontos_queda(
            resultado_historico
        )

        pontos_menor_preco = 0

        if resultado_historico.menor_preco_historico:
            pontos_menor_preco = (
                self.PONTOS_MENOR_PRECO_HISTORICO
            )

        return (
            pontos_queda
            + pontos_menor_preco
        )

    def _calcular_pontos_queda(
        self,
        resultado_historico: ResultadoHistoricoPreco
    ) -> float:
        if not resultado_historico.preco_caiu:
            return 0

        percentual_queda = abs(
            resultado_historico.variacao_percentual
        )

        percentual_limitado = min(
            percentual_queda,
            self.QUEDA_PERCENTUAL_PARA_PONTUACAO_MAXIMA
        )

        proporcao_queda = (
            percentual_limitado
            / self.QUEDA_PERCENTUAL_PARA_PONTUACAO_MAXIMA
        )

        return (
            proporcao_queda
            * self.PONTOS_MAXIMOS_QUEDA_PRECO
        )