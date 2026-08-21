# 63.8738, -149.7525

"""Regra de urgência por horário.

Durante a madrugada o canal tem pouca audiência. Ofertas apenas boas
ficam guardadas para a próxima janela de maior audiência. Nesse período,
só passam promoções realmente relâmpago, com histórico suficiente e
queda forte de preço.

Quedas extremas também são seguradas: elas podem ser preço bugado,
variação errada ou anúncio problemático e serão tratadas pela futura
camada de detecção/validação de anomalias.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco


@dataclass(frozen=True)
class ResultadoJanelaPublicacao:
    pode_publicar: bool
    motivo: str


class JanelaPublicacao:
    """Decide se uma oferta pode ser publicada no horário atual."""

    def __init__(
        self,
        hora_inicio_madrugada: int = 23,
        hora_fim_madrugada: int = 8,
        queda_minima_madrugada: float = 25.0,
        pontuacao_minima_madrugada: float = 90.0,
        registros_minimos_madrugada: int = 3,
        nota_comprador_minima_madrugada: float = 60.0,
        queda_minima_menor_preco_madrugada: float = 15.0,
        queda_maxima_automatica_madrugada: float = 55.0,
        ativa: bool = True,
    ) -> None:
        self.hora_inicio_madrugada = hora_inicio_madrugada
        self.hora_fim_madrugada = hora_fim_madrugada
        self.queda_minima_madrugada = queda_minima_madrugada
        self.pontuacao_minima_madrugada = pontuacao_minima_madrugada
        self.registros_minimos_madrugada = registros_minimos_madrugada
        self.nota_comprador_minima_madrugada = nota_comprador_minima_madrugada
        self.queda_minima_menor_preco_madrugada = queda_minima_menor_preco_madrugada
        self.queda_maxima_automatica_madrugada = queda_maxima_automatica_madrugada
        self.ativa = ativa

    def esta_na_madrugada(self, momento: datetime | None = None) -> bool:
        agora = momento or datetime.now()
        hora = agora.hour

        if self.hora_inicio_madrugada == self.hora_fim_madrugada:
            return False

        if self.hora_inicio_madrugada < self.hora_fim_madrugada:
            return self.hora_inicio_madrugada <= hora < self.hora_fim_madrugada

        return hora >= self.hora_inicio_madrugada or hora < self.hora_fim_madrugada

    def avaliar(
        self,
        oferta: Oferta,
        pontuacao: float,
        resultado_historico: ResultadoHistoricoPreco | None = None,
        momento: datetime | None = None,
    ) -> ResultadoJanelaPublicacao:
        if not self.ativa:
            return ResultadoJanelaPublicacao(True, "Restrição por horário desativada.")

        if not self.esta_na_madrugada(momento):
            return ResultadoJanelaPublicacao(True, "Horário de audiência normal.")

        if (
            oferta.tipo_oportunidade in {"possivel_preco_bugado", "anomalia_forte"}
            and oferta.anomalia_publicavel
        ):
            return ResultadoJanelaPublicacao(
                True,
                (
                    "Anomalia de preço validada pela camada reforçada: "
                    f"queda de {oferta.queda_anomala_percentual:.1f}%."
                ),
            )

        if resultado_historico is None or resultado_historico.primeiro_registro:
            return self._adiar("Histórico insuficiente para liberar uma oferta de madrugada.")

        if resultado_historico.quantidade_registros < self.registros_minimos_madrugada:
            return self._adiar(
                "Poucas verificações no histórico para classificar a oferta como relâmpago."
            )

        queda = self._obter_queda_percentual(resultado_historico)
        menor_preco = self._eh_menor_preco_historico(resultado_historico)
        nota_comprador = max(oferta.nota_tecnica + oferta.nota_historica, 0.0)

        if queda > self.queda_maxima_automatica_madrugada:
            return self._adiar(
                f"Queda anormal de {queda:.1f}%: aguardando validação reforçada antes de publicar."
            )

        if nota_comprador < self.nota_comprador_minima_madrugada:
            return self._adiar(
                f"Nota para o comprador insuficiente ({nota_comprador:.1f}/80) para a madrugada."
            )

        if (
            menor_preco
            and queda >= self.queda_minima_menor_preco_madrugada
            and pontuacao >= self.pontuacao_minima_madrugada
        ):
            return ResultadoJanelaPublicacao(
                True,
                (
                    "Oferta relâmpago: novo menor preço, "
                    f"queda de {queda:.1f}% e pontuação {pontuacao:.1f}."
                ),
            )

        if queda >= self.queda_minima_madrugada and pontuacao >= self.pontuacao_minima_madrugada:
            return ResultadoJanelaPublicacao(
                True,
                ("Oferta relâmpago: queda forte de " f"{queda:.1f}% e pontuação {pontuacao:.1f}."),
            )

        return self._adiar(
            "Madrugada: a oferta é boa, mas não é excepcional o bastante para publicar agora."
        )

    def _adiar(self, motivo: str) -> ResultadoJanelaPublicacao:
        return ResultadoJanelaPublicacao(pode_publicar=False, motivo=motivo)

    def _eh_menor_preco_historico(
        self,
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> bool:
        if resultado_historico is None or resultado_historico.primeiro_registro:
            return False

        return bool(resultado_historico.menor_preco_historico)

    def _obter_queda_percentual(
        self,
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> float:
        if resultado_historico is None or not resultado_historico.preco_caiu:
            return 0.0

        return abs(float(resultado_historico.variacao_percentual))
