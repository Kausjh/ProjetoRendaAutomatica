from models.oferta import Oferta
from services.curadoria_comercial import CuradoriaComercial
from services.historico_precos_service import ResultadoHistoricoPreco


class PontuadorOferta:
    """
    Pontuação máxima total: 100 pontos.

    Distribuição:

    - Nicho: 20
    - Desconto: 30
    - Preço: 15
    - Histórico: 15
    - Potencial comercial: 20
    """

    PONTOS_MAXIMOS_NICHO = 20.0
    PONTOS_MAXIMOS_DESCONTO = 30.0
    PONTOS_MAXIMOS_PRECO = 15.0
    PONTOS_MAXIMOS_QUEDA_PRECO = 10.0
    PONTOS_MENOR_PRECO_HISTORICO = 5.0
    PONTOS_MAXIMOS_COMERCIAL = 20.0

    DESCONTO_PARA_PONTUACAO_MAXIMA = 40.0
    QUEDA_PERCENTUAL_PARA_PONTUACAO_MAXIMA = 20.0

    def __init__(self, preco_maximo: float) -> None:
        if preco_maximo <= 0:
            raise ValueError("O preço máximo precisa ser maior que zero.")

        self.preco_maximo = preco_maximo
        self.curadoria_comercial = CuradoriaComercial()

    def calcular(
        self, oferta: Oferta, resultado_historico: ResultadoHistoricoPreco | None = None
    ) -> float:
        pontos_nicho = self._calcular_pontos_nicho(oferta)

        pontos_desconto = self._calcular_pontos_desconto(oferta)

        pontos_preco = self._calcular_pontos_preco(oferta)

        pontos_historico = self._calcular_pontos_historico(resultado_historico)

        resultado_comercial = self.curadoria_comercial.analisar(oferta)

        pontos_comerciais = min(resultado_comercial.nota, self.PONTOS_MAXIMOS_COMERCIAL)

        pontos_tecnicos = pontos_nicho + pontos_desconto + pontos_preco

        pontuacao_total = pontos_tecnicos + pontos_historico + pontos_comerciais

        pontuacao_total = round(min(max(pontuacao_total, 0.0), 100.0), 2)

        oferta.marca = resultado_comercial.marca
        oferta.nota_comercial = round(pontos_comerciais, 2)
        oferta.motivos_comerciais = list(resultado_comercial.motivos)
        oferta.nota_tecnica = round(pontos_tecnicos, 2)
        oferta.nota_historica = round(pontos_historico, 2)
        oferta.nota_final = pontuacao_total

        return pontuacao_total

    def _calcular_pontos_nicho(self, oferta: Oferta) -> float:
        if not oferta.eh_nicho:
            return 0.0

        relevancia_limitada = min(max(oferta.relevancia_nicho, 0.0), 100.0)

        proporcao_relevancia = relevancia_limitada / 100.0

        return proporcao_relevancia * self.PONTOS_MAXIMOS_NICHO

    def _calcular_pontos_desconto(self, oferta: Oferta) -> float:
        desconto = max(oferta.desconto_percentual, 0.0)

        desconto_limitado = min(desconto, self.DESCONTO_PARA_PONTUACAO_MAXIMA)

        proporcao_desconto = desconto_limitado / self.DESCONTO_PARA_PONTUACAO_MAXIMA

        return proporcao_desconto * self.PONTOS_MAXIMOS_DESCONTO

    def _calcular_pontos_preco(self, oferta: Oferta) -> float:
        if oferta.preco <= 0:
            return 0.0

        if oferta.preco > self.preco_maximo:
            return 0.0

        # Evita dar nota máxima apenas para produtos
        # extremamente baratos e de baixa comissão.
        if oferta.preco < 30:
            return 0.0

        if oferta.preco < 50:
            return 2.0

        if oferta.preco <= 300:
            return 11.0

        if oferta.preco <= 900:
            return self.PONTOS_MAXIMOS_PRECO

        if oferta.preco <= 1500:
            return 13.0

        return 10.0

    def _calcular_pontos_historico(
        self, resultado_historico: ResultadoHistoricoPreco | None
    ) -> float:
        if resultado_historico is None:
            return 0.0

        if resultado_historico.primeiro_registro:
            return 0.0

        pontos_queda = self._calcular_pontos_queda(resultado_historico)

        pontos_menor_preco = 0.0

        if resultado_historico.menor_preco_historico:
            pontos_menor_preco = self.PONTOS_MENOR_PRECO_HISTORICO

        return min(pontos_queda + pontos_menor_preco, 15.0)

    def _calcular_pontos_queda(self, resultado_historico: ResultadoHistoricoPreco) -> float:
        if not resultado_historico.preco_caiu:
            return 0.0

        percentual_queda = abs(resultado_historico.variacao_percentual)

        percentual_limitado = min(percentual_queda, self.QUEDA_PERCENTUAL_PARA_PONTUACAO_MAXIMA)

        proporcao_queda = percentual_limitado / self.QUEDA_PERCENTUAL_PARA_PONTUACAO_MAXIMA

        return proporcao_queda * self.PONTOS_MAXIMOS_QUEDA_PRECO
