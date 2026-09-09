# 63.8738, -149.7525

from __future__ import annotations

from models.oferta import Oferta
from services.curadoria_comercial import CuradoriaComercial
from services.historico_precos_service import (
    ResultadoHistoricoPreco,
)
from services.inteligencia_produto import (
    InteligenciaProduto,
    ResultadoInteligenciaProduto,
)


class PontuadorOferta:
    """Pontua oportunidade real para o comprador.

    Total: 100 pontos.

    Dimensoes observaveis:
    - nicho: 10
    - desconto anunciado: 10
    - Product Intelligence: 20
    - curadoria do comprador: 20

    Evidencia historica:
    - queda real: 20
    - novo menor preco: 15
    - maturidade: 5

    Product Quality != Deal Quality.

    A nota do produto existe independentemente do preco,
    mas seus pontos de Deal Score exigem algum sinal de preco.
    """

    PONTOS_MAXIMOS_NICHO = 10.0
    PONTOS_MAXIMOS_DESCONTO_ANUNCIADO = 10.0
    PONTOS_MAXIMOS_PRODUTO = 20.0

    PONTOS_MAXIMOS_QUEDA_REAL = 20.0
    PONTOS_NOVO_MENOR_PRECO = 15.0
    PONTOS_MAXIMOS_MATURIDADE_HISTORICO = 5.0

    PONTOS_MAXIMOS_CURADORIA = 20.0

    DESCONTO_ANUNCIADO_PARA_MAXIMO = 40.0
    QUEDA_REAL_PARA_MAXIMO = 20.0
    REGISTROS_PARA_MATURIDADE_MAXIMA = 10

    def __init__(
        self,
        preco_maximo: float,
    ) -> None:
        if preco_maximo <= 0:
            raise ValueError("O preco maximo precisa ser maior que zero.")

        self.preco_maximo = preco_maximo

        self.curadoria_comercial = CuradoriaComercial()

        self.inteligencia_produto = InteligenciaProduto()

    def calcular(
        self,
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None = None,
    ) -> float:
        resultado_produto = self.inteligencia_produto.aplicar(oferta)

        resultado_comercial = self.curadoria_comercial.analisar(oferta)

        oferta.marca = resultado_comercial.marca or resultado_produto.marca

        oferta.nota_comercial = round(
            float(resultado_comercial.nota),
            2,
        )

        oferta.motivos_comerciais = list(resultado_comercial.motivos)

        pontos_nicho = self._calcular_pontos_nicho(oferta)

        pontos_desconto = self._calcular_pontos_desconto_anunciado(oferta)

        pontos_queda = self._calcular_pontos_queda_real(resultado_historico)

        pontos_menor = self._calcular_pontos_novo_menor_preco(resultado_historico)

        pontos_maturidade = self._calcular_pontos_maturidade(resultado_historico)

        pontos_curadoria = self._calcular_pontos_curadoria(oferta)

        pontos_produto = self._calcular_pontos_produto(
            oferta=oferta,
            resultado_produto=resultado_produto,
            resultado_historico=resultado_historico,
        )

        pontos_historicos = pontos_queda + pontos_menor + pontos_maturidade

        pontos_tecnicos = pontos_nicho + pontos_desconto + pontos_produto + pontos_curadoria

        total = round(
            min(
                max(
                    pontos_tecnicos + pontos_historicos,
                    0.0,
                ),
                100.0,
            ),
            2,
        )

        oferta.nota_tecnica = round(
            pontos_tecnicos,
            2,
        )

        oferta.nota_historica = round(
            pontos_historicos,
            2,
        )

        oferta.nota_final = total

        oferta.componentes_pontuacao = {
            "nicho": round(
                pontos_nicho,
                2,
            ),
            "desconto_anunciado": round(
                pontos_desconto,
                2,
            ),
            "inteligencia_produto": round(
                pontos_produto,
                2,
            ),
            "inteligencia_produto_nota": round(
                float(resultado_produto.nota),
                2,
            ),
            "queda_real_historico": round(
                pontos_queda,
                2,
            ),
            "novo_menor_preco": round(
                pontos_menor,
                2,
            ),
            "maturidade_historico": round(
                pontos_maturidade,
                2,
            ),
            "curadoria_comprador": round(
                pontos_curadoria,
                2,
            ),
            "potencial_comercial_no_score": 0.0,
        }

        return total

    def _calcular_pontos_nicho(
        self,
        oferta: Oferta,
    ) -> float:
        if not oferta.eh_nicho:
            return 0.0

        relevancia = min(
            max(
                float(oferta.relevancia_nicho),
                0.0,
            ),
            100.0,
        )

        return relevancia / 100.0 * self.PONTOS_MAXIMOS_NICHO

    def _calcular_pontos_desconto_anunciado(
        self,
        oferta: Oferta,
    ) -> float:
        desconto = max(
            float(oferta.desconto_percentual),
            0.0,
        )

        desconto = min(
            desconto,
            self.DESCONTO_ANUNCIADO_PARA_MAXIMO,
        )

        return (
            desconto / self.DESCONTO_ANUNCIADO_PARA_MAXIMO * self.PONTOS_MAXIMOS_DESCONTO_ANUNCIADO
        )

    def _calcular_pontos_produto(
        self,
        *,
        oferta: Oferta,
        resultado_produto: ResultadoInteligenciaProduto,
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> float:
        tem_desconto = oferta.desconto_percentual > 0

        tem_queda = bool(
            resultado_historico is not None
            and not resultado_historico.primeiro_registro
            and resultado_historico.preco_caiu
        )

        tem_novo_minimo = bool(
            resultado_historico is not None
            and not resultado_historico.primeiro_registro
            and resultado_historico.menor_preco_historico
        )

        if not (tem_desconto or tem_queda or tem_novo_minimo):
            return 0.0

        nota = min(
            max(
                float(resultado_produto.nota),
                0.0,
            ),
            100.0,
        )

        return nota / 100.0 * self.PONTOS_MAXIMOS_PRODUTO

    def _calcular_pontos_queda_real(
        self,
        resultado: ResultadoHistoricoPreco | None,
    ) -> float:
        if resultado is None or resultado.primeiro_registro:
            return 0.0

        if not resultado.preco_caiu:
            return 0.0

        queda = min(
            abs(float(resultado.variacao_percentual)),
            self.QUEDA_REAL_PARA_MAXIMO,
        )

        return queda / self.QUEDA_REAL_PARA_MAXIMO * self.PONTOS_MAXIMOS_QUEDA_REAL

    def _calcular_pontos_novo_menor_preco(
        self,
        resultado: ResultadoHistoricoPreco | None,
    ) -> float:
        if resultado is None or resultado.primeiro_registro:
            return 0.0

        if not resultado.menor_preco_historico:
            return 0.0

        return self.PONTOS_NOVO_MENOR_PRECO

    def _calcular_pontos_maturidade(
        self,
        resultado: ResultadoHistoricoPreco | None,
    ) -> float:
        if resultado is None or resultado.primeiro_registro:
            return 0.0

        quantidade = min(
            max(
                int(resultado.quantidade_registros),
                0,
            ),
            self.REGISTROS_PARA_MATURIDADE_MAXIMA,
        )

        return (
            quantidade
            / self.REGISTROS_PARA_MATURIDADE_MAXIMA
            * self.PONTOS_MAXIMOS_MATURIDADE_HISTORICO
        )

    def _calcular_pontos_curadoria(
        self,
        oferta: Oferta,
    ) -> float:
        nota = min(
            max(
                float(oferta.nota_curadoria),
                0.0,
            ),
            100.0,
        )

        return nota / 100.0 * self.PONTOS_MAXIMOS_CURADORIA
