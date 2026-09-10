# 63.8738, -149.7525

from __future__ import annotations

import logging
import threading
from pathlib import Path

from repositories.historico_comercial_scout_repository import (
    HistoricoComercialScoutRepository,
)
from repositories.resolucoes_scout_repository import (
    ResolucoesScoutRepository,
)
from repositories.sinais_scout_repository import (
    SinaisScoutRepository,
)
from services.scout.awin_destino_resolver import (
    AwinDestinoResolver,
)
from services.scout.awin_promotions_sensor import (
    AwinPromotionsSensor,
)
from services.scout.ciclo_partner_scout import (
    CicloPartnerScout,
    ResultadoCicloPartnerScout,
)
from services.scout.historico_comercial_scout import (
    HistoricoComercialScout,
)
from services.scout.radar_scout import (
    RadarScout,
    SensorScout,
)
from services.scout.resolvedor_scout import (
    ResolvedorSinalScout,
)

logger = logging.getLogger(__name__)


INTERVALO_PADRAO_SEGUNDOS = 1800.0


class PartnerScoutWorker:
    """
    Worker continuo do Partner Scout.

    O worker apenas agenda ciclos do CicloPartnerScout.

    Ele nao:
    - altera budget do Hunter;
    - publica ofertas;
    - altera historico de preco;
    - transforma sinal comercial em preco oficial.
    """

    def __init__(
        self,
        ciclo: CicloPartnerScout,
        *,
        intervalo_segundos: float = INTERVALO_PADRAO_SEGUNDOS,
    ) -> None:
        intervalo = float(intervalo_segundos)

        if intervalo <= 0:
            raise ValueError("intervalo_segundos deve ser maior que zero.")

        self.ciclo = ciclo
        self.intervalo_segundos = intervalo

        self._parada = threading.Event()

    def solicitar_parada(
        self,
    ) -> None:
        self._parada.set()

    def executar_ciclo(
        self,
    ) -> ResultadoCicloPartnerScout:
        resultado = self.ciclo.executar()

        logger.info(
            "Partner Scout: ciclo concluido | "
            "recebidos=%d | novos=%d | atualizados=%d | "
            "inalterados=%d | eventos_comerciais=%d | "
            "historicos=%d | falhas_resolucao=%d | "
            "falhas_historico=%d.",
            resultado.radar.sinais_recebidos,
            resultado.radar.novos,
            resultado.radar.atualizados,
            resultado.radar.inalterados,
            resultado.eventos_comerciais,
            resultado.historicos_registrados,
            resultado.falhas_resolucao,
            resultado.falhas_historico,
        )

        return resultado

    def executar(
        self,
        maximo_ciclos: int | None = None,
    ) -> int:
        if maximo_ciclos is not None and maximo_ciclos <= 0:
            raise ValueError("maximo_ciclos deve ser maior que zero.")

        ciclos = 0

        logger.info(
            "Partner Scout Worker iniciado " "com intervalo de %.2f segundos.",
            self.intervalo_segundos,
        )

        while not self._parada.is_set():

            try:
                self.executar_ciclo()

            except Exception:
                logger.exception("Partner Scout: falha inesperada no ciclo.")

            ciclos += 1

            if maximo_ciclos is not None and ciclos >= maximo_ciclos:
                break

            if self._parada.wait(self.intervalo_segundos):
                break

        logger.info("Partner Scout Worker encerrado.")

        return ciclos


def criar_partner_scout_worker(
    *,
    intervalo_segundos: float = INTERVALO_PADRAO_SEGUNDOS,
    caminho_scout: str | Path = ("database/sinais_scout.sqlite3"),
    caminho_historico: str | Path = ("database/historico_comercial_scout.sqlite3"),
    sensores: list[SensorScout] | None = None,
    resolvedores: list[ResolvedorSinalScout] | None = None,
) -> PartnerScoutWorker:
    """
    Monta a composicao real do Partner Scout.

    A construcao pode receber caminhos/sensores alternativos para
    canarios e testes sem tocar nos bancos de producao.
    """

    sinais_repository = SinaisScoutRepository(caminho_scout)

    resolucoes_repository = ResolucoesScoutRepository(caminho_scout)

    historico_repository = HistoricoComercialScoutRepository(caminho_historico)

    if sensores is None:
        sensores = [
            AwinPromotionsSensor(),
        ]

    if resolvedores is None:
        resolvedores = [
            AwinDestinoResolver(),
        ]

    radar = RadarScout(
        sensores=list(sensores),
        repository=sinais_repository,
    )

    historico = HistoricoComercialScout(historico_repository)

    ciclo = CicloPartnerScout(
        radar=radar,
        resolvedores=list(resolvedores),
        resolucoes_repository=(resolucoes_repository),
        historico=historico,
    )

    return PartnerScoutWorker(
        ciclo=ciclo,
        intervalo_segundos=intervalo_segundos,
    )
