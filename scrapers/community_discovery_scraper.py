# 63.8738, -149.7525

from __future__ import annotations

import logging

from models.oferta import Oferta
from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from scrapers.base_scraper import BaseScraper
from services.community_discovery_marketplace_adapter import (
    CommunityDiscoveryMarketplaceAdapter,
)
from services.community_discovery_queue_service import (
    CommunityDiscoveryQueueService,
)

logger = logging.getLogger(__name__)


class CommunityDiscoveryScraper(BaseScraper):
    VERSAO_PROCESSADOR = "community_discovery_worker_v1"

    STATUS_OFERTA_CRIADA = "oferta_criada"
    STATUS_RETRY = "retry"
    STATUS_REJEITADA = "rejeitada"
    STATUS_NAO_SUPORTADA = "nao_suportada"

    HANDOFFS_APROVADOS = frozenset(
        {
            "pipeline_processada",
            "coletor_duplicada",
        }
    )

    def __init__(
        self,
        *,
        queue_service: CommunityDiscoveryQueueService | None = None,
        adapter: CommunityDiscoveryMarketplaceAdapter | None = None,
        caminho_banco: str = "database/user_identity.sqlite3",
        max_descobertas_por_execucao: int = 3,
    ) -> None:
        if queue_service is None:
            repository = CommunityDiscoveryRepository(caminho_banco)
            queue_service = CommunityDiscoveryQueueService(repository)

        self.queue_service = queue_service
        self.adapter = adapter or CommunityDiscoveryMarketplaceAdapter()
        self.max_descobertas_por_execucao = max(
            int(max_descobertas_por_execucao),
            1,
        )

        self._handoffs_pendentes: dict[
            int,
            tuple[Oferta, str],
        ] = {}

    def buscar_ofertas(
        self,
        limite: int = 5,
    ) -> list[Oferta]:
        limite = max(int(limite), 0)

        if limite <= 0:
            return []

        limite_reserva = min(
            limite,
            self.max_descobertas_por_execucao,
        )

        try:
            descobertas = self.queue_service.reservar(
                limite=limite_reserva,
            )
        except Exception:
            logger.exception("Falha ao reservar Descobertas Comunitarias.")
            return []

        ofertas: list[Oferta] = []

        for descoberta in descobertas:
            try:
                resultado = self.adapter.processar(descoberta)
            except Exception as erro:
                self._registrar_erro_seguro(
                    descoberta.id,
                    erro=("community_discovery_adapter_exception:" f"{type(erro).__name__}"),
                    transitorio=True,
                )
                continue

            if resultado.status == self.STATUS_OFERTA_CRIADA and resultado.oferta is not None:
                self._registrar_handoff_pendente(
                    oferta=resultado.oferta,
                    descoberta_id=descoberta.id,
                )
                ofertas.append(resultado.oferta)
                continue

            if resultado.status == self.STATUS_RETRY or resultado.transitorio:
                self._registrar_erro_seguro(
                    descoberta.id,
                    erro=(resultado.motivo or "community_discovery_retry"),
                    transitorio=True,
                )
                continue

            if resultado.status in {
                self.STATUS_REJEITADA,
                self.STATUS_NAO_SUPORTADA,
            }:
                self._rejeitar_seguro(
                    descoberta.id,
                    motivo=(resultado.motivo or "community_discovery_rejeitada"),
                )
                continue

            self._registrar_erro_seguro(
                descoberta.id,
                erro=("status_adapter_inesperado:" f"{resultado.status}"),
                transitorio=True,
            )

        logger.info(
            "CommunityDiscoveryScraper reservou %s item(ns) e " "emitiu %s oferta(s).",
            len(descobertas),
            len(ofertas),
        )

        return ofertas

    def confirmar_handoff(
        self,
        oferta: Oferta,
        *,
        status: str,
        motivo: str,
    ) -> bool:
        chave_oferta = id(oferta)
        registro = self._handoffs_pendentes.get(chave_oferta)

        if registro is None:
            return False

        oferta_pendente, descoberta_id = registro

        if oferta_pendente is not oferta:
            return False

        status_normalizado = str(status or "").strip()
        motivo_normalizado = str(motivo or "").strip()
        motivo_terminal = (
            f"{status_normalizado}:{motivo_normalizado}"
            if motivo_normalizado
            else status_normalizado
        ) or "handoff_downstream_sem_motivo"

        try:
            if status_normalizado in self.HANDOFFS_APROVADOS:
                canonical_key = (
                    str(
                        getattr(
                            oferta,
                            "chave_produto_canonica",
                            "",
                        )
                        or ""
                    ).strip()
                    or None
                )

                self.queue_service.aprovar(
                    descoberta_id,
                    canonical_key=canonical_key,
                    motivo=motivo_terminal,
                )
            else:
                self.queue_service.rejeitar(
                    descoberta_id,
                    motivo=motivo_terminal,
                )
        except Exception:
            logger.exception(
                "Falha ao confirmar handoff da Descoberta " "Comunitaria id=%s status=%s.",
                descoberta_id,
                status_normalizado,
            )
            return False

        self._handoffs_pendentes.pop(chave_oferta, None)
        return True

    def _registrar_handoff_pendente(
        self,
        *,
        oferta: Oferta,
        descoberta_id: str,
    ) -> None:
        self._handoffs_pendentes[id(oferta)] = (
            oferta,
            str(descoberta_id),
        )

    def _registrar_erro_seguro(
        self,
        descoberta_id: str,
        *,
        erro: object,
        transitorio: bool,
    ) -> bool:
        try:
            self.queue_service.registrar_erro(
                descoberta_id,
                erro=erro,
                transitorio=transitorio,
            )
            return True
        except Exception:
            logger.exception(
                "Falha ao registrar erro da Descoberta " "Comunitaria id=%s.",
                descoberta_id,
            )
            return False

    def _rejeitar_seguro(
        self,
        descoberta_id: str,
        *,
        motivo: str,
    ) -> bool:
        try:
            self.queue_service.rejeitar(
                descoberta_id,
                motivo=motivo,
            )
            return True
        except Exception:
            logger.exception(
                "Falha ao rejeitar Descoberta Comunitaria id=%s.",
                descoberta_id,
            )
            return False
