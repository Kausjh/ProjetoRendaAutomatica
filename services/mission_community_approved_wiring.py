from __future__ import annotations

from models.mission_community import (
    DescobertaAprovadaParaMissao,
    ResultadoWiringMissaoCommunity,
)
from services.mission_production_catalog import (
    COMMUNITY_APPROVED_EVENT,
    CatalogoMissoesProducao,
)
from services.mission_service import (
    MissionService,
)


class MissionCommunityApprovedWiring:
    def __init__(
        self,
        *,
        mission_service: MissionService,
        catalogo: CatalogoMissoesProducao,
    ) -> None:
        self.mission_service = mission_service
        self.catalogo = catalogo

    def processar_aprovacao(
        self,
        *,
        descoberta_id: str,
        conta_id: str,
        status: str,
        ocorrido_em: str,
    ) -> ResultadoWiringMissaoCommunity:
        descoberta = DescobertaAprovadaParaMissao(
            id=str(descoberta_id or "").strip(),
            conta_id=str(conta_id or "").strip(),
            status=str(status or "").strip(),
            ocorrido_em=str(ocorrido_em or "").strip(),
        )

        return self.processar(descoberta)

    def processar(
        self,
        descoberta: DescobertaAprovadaParaMissao,
    ) -> ResultadoWiringMissaoCommunity:
        falhas: list[str] = []

        if not descoberta.id:
            falhas.append("descoberta_id_ausente")

        if not descoberta.conta_id:
            falhas.append("conta_id_ausente")

        if descoberta.status != "approved":
            falhas.append("status_nao_aprovado")

        if not descoberta.ocorrido_em:
            falhas.append("ocorrido_em_ausente")

        if falhas:
            return ResultadoWiringMissaoCommunity(
                descoberta_id=descoberta.id,
                status="error",
                eventos_criados=0,
                eventos_idempotentes=0,
                eventos_completados=0,
                missoes_concluidas_agora=0,
                recompensas_criadas=0,
                falhas=tuple(falhas),
            )

        missoes = self.catalogo.ruleset.listar_por_evento(COMMUNITY_APPROVED_EVENT)

        eventos_criados = 0
        eventos_idempotentes = 0
        eventos_completados = 0
        missoes_concluidas_agora = 0
        recompensas_criadas = 0

        chave = self.catalogo.chave_idempotencia_aprovacao(descoberta.id)

        for missao in missoes:
            try:
                resultado = self.mission_service.registrar_evento(
                    conta_id=(descoberta.conta_id),
                    missao_codigo=(missao.codigo),
                    tipo_evento=(COMMUNITY_APPROVED_EVENT),
                    origem=(self.catalogo.origem_evento),
                    origem_id=(descoberta.id),
                    chave_idempotencia=chave,
                    instancia_chave=(self.catalogo.derivar_instancia_chave(missao.codigo)),
                    metadados={
                        "status": "approved",
                    },
                    ocorrido_em=(descoberta.ocorrido_em),
                )

                if resultado.status == "created":
                    eventos_criados += 1

                elif resultado.status == "idempotent":
                    eventos_idempotentes += 1

                elif resultado.status == "completed":
                    eventos_completados += 1

                else:
                    falhas.append(f"{missao.codigo}:" f"status_inesperado:" f"{resultado.status}")

                if resultado.concluida_agora:
                    missoes_concluidas_agora += 1

                if resultado.recompensa_criada:
                    recompensas_criadas += 1

            except Exception as erro:
                falhas.append(f"{missao.codigo}:" f"{type(erro).__name__}:" f"{erro}")

        return ResultadoWiringMissaoCommunity(
            descoberta_id=descoberta.id,
            status=("success" if not falhas else "error"),
            eventos_criados=eventos_criados,
            eventos_idempotentes=(eventos_idempotentes),
            eventos_completados=(eventos_completados),
            missoes_concluidas_agora=(missoes_concluidas_agora),
            recompensas_criadas=(recompensas_criadas),
            falhas=tuple(falhas),
        )
