# 63.8738, -149.7525

from __future__ import annotations

import logging
from dataclasses import dataclass

from models.plano_discovery_scout import (
    PlanoDiscoveryScout,
)
from models.resolucao_scout import ResolucaoScout
from models.sinal_scout import SinalScout
from repositories.resolucoes_scout_repository import (
    ResolucoesScoutRepository,
)
from services.scout.historico_comercial_scout import (
    HistoricoComercialScout,
)
from services.scout.inteligencia_comercial_scout import (
    InteligenciaComercialScout,
)
from services.scout.planejador_discovery_scout import (
    PlanejadorDiscoveryScout,
)
from services.scout.radar_scout import (
    RadarScout,
    ResultadoRadarScout,
)
from services.scout.resolvedor_scout import (
    ResolvedorSinalScout,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResultadoCicloPartnerScout:
    radar: ResultadoRadarScout

    eventos_comerciais: int
    resolucoes_persistidas: int
    historicos_registrados: int

    planos_utilizaveis: int

    falhas_resolucao: int
    falhas_planejamento: int
    falhas_persistencia_resolucao: int
    falhas_historico: int


class CicloPartnerScout:
    """
    Conecta mudancas reais do Radar Scout ao historico comercial.

    Somente eventos classificados pelo Radar como:
    - novo;
    - atualizado;

    geram observacao comercial.

    Eventos inalterados sao ignorados e, portanto, sinais antigos
    ja existentes no banco nao sao retroativamente importados.
    """

    EVENTOS_COMERCIAIS = frozenset(
        {
            "novo",
            "atualizado",
        }
    )

    def __init__(
        self,
        *,
        radar: RadarScout,
        resolvedores: list[ResolvedorSinalScout],
        resolucoes_repository: ResolucoesScoutRepository,
        historico: HistoricoComercialScout,
        planejador: PlanejadorDiscoveryScout | None = None,
        inteligencia: InteligenciaComercialScout | None = None,
    ) -> None:
        self.radar = radar
        self.resolvedores = list(resolvedores)

        self.resolucoes_repository = resolucoes_repository

        self.historico = historico

        self.planejador = planejador or PlanejadorDiscoveryScout()

        self.inteligencia = inteligencia or InteligenciaComercialScout()

    def executar(
        self,
    ) -> ResultadoCicloPartnerScout:
        resultado_radar = self.radar.executar()

        eventos_comerciais = 0
        resolucoes_persistidas = 0
        historicos_registrados = 0
        planos_utilizaveis = 0

        falhas_resolucao = 0
        falhas_planejamento = 0
        falhas_persistencia_resolucao = 0
        falhas_historico = 0

        for evento in resultado_radar.eventos:

            tipo_evento = str(evento.resultado or "").strip().casefold()

            if tipo_evento not in self.EVENTOS_COMERCIAIS:
                continue

            eventos_comerciais += 1

            sinal = evento.sinal

            (
                resolucao,
                falhou_resolucao,
            ) = self._resolver(sinal)

            if falhou_resolucao:
                falhas_resolucao += 1

            try:
                self.resolucoes_repository.salvar(resolucao)

                resolucoes_persistidas += 1

            except Exception:
                falhas_persistencia_resolucao += 1

                logger.exception(
                    "Partner Scout: falha ao persistir " "resolucao %s/%s.",
                    sinal.fonte,
                    sinal.id_externo,
                )

            plano: PlanoDiscoveryScout | None = None

            if str(resolucao.status or "").strip().casefold() == "landing_page":
                try:
                    plano = self.planejador.planejar(
                        sinal,
                        resolucao,
                    )

                    if plano.utilizavel:
                        planos_utilizaveis += 1

                except Exception:
                    falhas_planejamento += 1

                    logger.exception(
                        "Partner Scout: falha ao planejar " "discovery %s/%s.",
                        sinal.fonte,
                        sinal.id_externo,
                    )

                    plano = None

            try:
                perfil = self.inteligencia.analisar(
                    sinal=sinal,
                    resolucao=resolucao,
                    plano=plano,
                )

                registrado = self.historico.registrar(
                    perfil=perfil,
                    tipo_evento=tipo_evento,
                )

                if registrado:
                    historicos_registrados += 1

            except Exception:
                falhas_historico += 1

                logger.exception(
                    "Partner Scout: falha ao registrar " "historico comercial %s/%s.",
                    sinal.fonte,
                    sinal.id_externo,
                )

        return ResultadoCicloPartnerScout(
            radar=resultado_radar,
            eventos_comerciais=eventos_comerciais,
            resolucoes_persistidas=(resolucoes_persistidas),
            historicos_registrados=(historicos_registrados),
            planos_utilizaveis=(planos_utilizaveis),
            falhas_resolucao=(falhas_resolucao),
            falhas_planejamento=(falhas_planejamento),
            falhas_persistencia_resolucao=(falhas_persistencia_resolucao),
            falhas_historico=(falhas_historico),
        )

    def _resolver(
        self,
        sinal: SinalScout,
    ) -> tuple[
        ResolucaoScout,
        bool,
    ]:
        resolvedor = next(
            (item for item in self.resolvedores if item.suporta(sinal)),
            None,
        )

        if resolvedor is None:
            return (
                ResolucaoScout(
                    fonte=sinal.fonte,
                    id_externo=sinal.id_externo,
                    status="nao_suportado",
                    motivo=("sem_resolvedor_para_fonte"),
                ),
                False,
            )

        try:
            return (
                resolvedor.resolver(sinal),
                False,
            )

        except Exception as erro:
            logger.exception(
                "Partner Scout: falha ao resolver " "sinal %s/%s.",
                sinal.fonte,
                sinal.id_externo,
            )

            return (
                ResolucaoScout(
                    fonte=sinal.fonte,
                    id_externo=sinal.id_externo,
                    status="erro",
                    motivo=("falha_resolvedor:" + type(erro).__name__),
                ),
                True,
            )
