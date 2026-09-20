# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass

from models.mission_community import (
    ResultadoWiringMissaoCommunity,
)
from services.mission_community_approved_wiring import (
    MissionCommunityApprovedWiring,
)
from services.mission_reward_settlement_service import (
    MissionRewardSettlementService,
    ResultadoLiquidacaoLote,
)


@dataclass(frozen=True, slots=True)
class ResultadoWiringMissaoCommunityLiveSettlement:
    descoberta_id: str
    mission_result: ResultadoWiringMissaoCommunity | None
    settlement_result: ResultadoLiquidacaoLote | None
    falhas: tuple[str, ...]

    @property
    def sucesso(self) -> bool:
        return not self.falhas


class MissionCommunityLiveSettlementWiring:
    """
    Compoe o wiring live de missoes com o settlement de rewards.

    A descoberta comunitaria ja foi persistida como approved antes deste
    hook ser chamado.

    Portanto:

    - falha de missao nao desfaz a descoberta;
    - falha de settlement nao desfaz a descoberta;
    - reward pending continua recuperavel;
    - o settlement existente preserva idempotencia pelo reward grant ID.
    """

    def __init__(
        self,
        *,
        mission_wiring: MissionCommunityApprovedWiring,
        settlement_service: MissionRewardSettlementService,
        limite_settlement: int = 100,
    ) -> None:
        if limite_settlement < 1:
            raise ValueError("limite_settlement precisa ser positivo.")

        self.mission_wiring = mission_wiring
        self.settlement_service = settlement_service
        self.limite_settlement = int(limite_settlement)

    def processar_aprovacao(
        self,
        *,
        descoberta_id: str,
        conta_id: str,
        status: str,
        ocorrido_em: str,
    ) -> ResultadoWiringMissaoCommunityLiveSettlement:
        falhas: list[str] = []

        mission_result = None
        settlement_result = None

        try:
            mission_result = self.mission_wiring.processar_aprovacao(
                descoberta_id=descoberta_id,
                conta_id=conta_id,
                status=status,
                ocorrido_em=ocorrido_em,
            )

            falhas.extend(f"mission:{falha}" for falha in mission_result.falhas)

        except Exception as erro:
            falhas.append("mission:" f"{type(erro).__name__}:" f"{erro}")

        # O sweep roda mesmo se a missao nao tiver criado reward agora.
        # Isso permite recuperar reward pending deixado por tentativa
        # anterior sem depender de restart do runtime.
        try:
            settlement_result = self.settlement_service.liquidar_pendentes(
                limite=self.limite_settlement,
            )

            falhas.extend(f"settlement:{falha}" for falha in settlement_result.falhas)

        except Exception as erro:
            falhas.append("settlement:" f"{type(erro).__name__}:" f"{erro}")

        return ResultadoWiringMissaoCommunityLiveSettlement(
            descoberta_id=str(descoberta_id or "").strip(),
            mission_result=mission_result,
            settlement_result=settlement_result,
            falhas=tuple(falhas),
        )
