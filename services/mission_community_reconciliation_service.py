from __future__ import annotations

from models.mission_community import (
    ResultadoReconciliacaoMissoes,
)
from repositories.mission_community_reconciliation_repository import (
    MissionCommunityReconciliationRepository,
)
from services.mission_community_approved_wiring import (
    MissionCommunityApprovedWiring,
)


class MissionCommunityReconciliationService:
    def __init__(
        self,
        *,
        repository: MissionCommunityReconciliationRepository,
        wiring: MissionCommunityApprovedWiring,
        tamanho_lote: int = 500,
    ) -> None:
        if tamanho_lote < 1:
            raise ValueError("tamanho_lote precisa " "ser positivo.")

        self.repository = repository
        self.wiring = wiring
        self.tamanho_lote = min(
            int(tamanho_lote),
            1000,
        )

    def reconciliar(
        self,
    ) -> ResultadoReconciliacaoMissoes:
        offset = 0

        descobertas_processadas = 0
        eventos_criados = 0
        eventos_idempotentes = 0
        eventos_completados = 0
        missoes_concluidas_agora = 0
        recompensas_criadas = 0
        falhas: list[str] = []

        while True:
            try:
                lote = self.repository.listar_aprovadas(
                    limite=(self.tamanho_lote),
                    offset=offset,
                )

            except Exception as erro:
                falhas.append("repository:" f"{type(erro).__name__}:" f"{erro}")
                break

            if not lote:
                break

            for descoberta in lote:
                descobertas_processadas += 1

                resultado = self.wiring.processar(descoberta)

                eventos_criados += resultado.eventos_criados

                eventos_idempotentes += resultado.eventos_idempotentes

                eventos_completados += resultado.eventos_completados

                missoes_concluidas_agora += resultado.missoes_concluidas_agora

                recompensas_criadas += resultado.recompensas_criadas

                if not resultado.sucesso:
                    for falha in resultado.falhas:
                        falhas.append(f"{descoberta.id}:" f"{falha}")

            offset += len(lote)

            if len(lote) < self.tamanho_lote:
                break

        return ResultadoReconciliacaoMissoes(
            descobertas_processadas=(descobertas_processadas),
            eventos_criados=eventos_criados,
            eventos_idempotentes=(eventos_idempotentes),
            eventos_completados=(eventos_completados),
            missoes_concluidas_agora=(missoes_concluidas_agora),
            recompensas_criadas=(recompensas_criadas),
            falhas=tuple(falhas),
        )
