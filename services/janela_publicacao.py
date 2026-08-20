# 63.8738, -149.7525

"""Regra de urgência por horário.

Durante a madrugada o canal tem pouca audiência. Publicar uma oferta
mediana nesse período gasta o estoque: ela fica marcada como publicada
e não volta mais.

Por outro lado, promoções relâmpago costumam aparecer justamente de
madrugada e não podem esperar o horário de pico.

A solução é elevar o critério à noite em vez de bloquear tudo: só
passam as ofertas realmente fortes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco

logger = logging.getLogger(__name__)


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
        queda_minima_madrugada: float = 15.0,
        pontuacao_minima_madrugada: float = 80.0,
        ativa: bool = True,
    ) -> None:
        self.hora_inicio_madrugada = hora_inicio_madrugada
        self.hora_fim_madrugada = hora_fim_madrugada
        self.queda_minima_madrugada = queda_minima_madrugada
        self.pontuacao_minima_madrugada = pontuacao_minima_madrugada
        self.ativa = ativa

    def esta_na_madrugada(self, momento: datetime | None = None) -> bool:
        agora = momento or datetime.now()

        hora = agora.hour

        if self.hora_inicio_madrugada == self.hora_fim_madrugada:
            return False

        if self.hora_inicio_madrugada < self.hora_fim_madrugada:
            return self.hora_inicio_madrugada <= hora < self.hora_fim_madrugada

        # Faixa que cruza a meia-noite (ex.: 23h às 8h).
        return hora >= self.hora_inicio_madrugada or hora < self.hora_fim_madrugada

    def avaliar(
        self,
        oferta: Oferta,
        pontuacao: float,
        resultado_historico: ResultadoHistoricoPreco | None = None,
        momento: datetime | None = None,
    ) -> ResultadoJanelaPublicacao:
        if not self.ativa:
            return ResultadoJanelaPublicacao(
                pode_publicar=True,
                motivo="Restrição por horário desativada.",
            )

        if not self.esta_na_madrugada(momento):
            return ResultadoJanelaPublicacao(
                pode_publicar=True,
                motivo="Horário de audiência normal.",
            )

        if self._eh_menor_preco_historico(resultado_historico):
            return ResultadoJanelaPublicacao(
                pode_publicar=True,
                motivo="Menor preço histórico registrado.",
            )

        queda = self._obter_queda_percentual(resultado_historico)

        if queda >= self.queda_minima_madrugada:
            return ResultadoJanelaPublicacao(
                pode_publicar=True,
                motivo=(f"Queda de {queda:.1f}% no preço."),
            )

        if pontuacao >= self.pontuacao_minima_madrugada:
            return ResultadoJanelaPublicacao(
                pode_publicar=True,
                motivo=(f"Pontuação alta ({pontuacao:.1f})."),
            )

        return ResultadoJanelaPublicacao(
            pode_publicar=False,
            motivo=(
                "Fora do horário de pico e sem urgência suficiente. "
                "Guardada para a próxima janela de audiência."
            ),
        )

    def _eh_menor_preco_historico(
        self,
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> bool:
        if resultado_historico is None:
            return False

        if resultado_historico.primeiro_registro:
            return False

        return bool(resultado_historico.menor_preco_historico)

    def _obter_queda_percentual(
        self,
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> float:
        if resultado_historico is None:
            return 0.0

        if not resultado_historico.preco_caiu:
            return 0.0

        return abs(float(resultado_historico.variacao_percentual))
