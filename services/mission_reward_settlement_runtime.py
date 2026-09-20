from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from repositories.gamification_repository import (
    GamificationRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.gamification_service import (
    GamificationService,
)
from services.mission_production_catalog import (
    criar_catalogo_missoes_producao_v1,
)
from services.mission_reward_settlement_service import (
    MissionRewardSettlementService,
    ResultadoLiquidacaoLote,
    criar_ruleset_gamificacao_com_rewards_missoes_v1,
)
from services.mission_service import (
    MissionService,
)


@dataclass(frozen=True, slots=True)
class ResultadoAtivacaoRewardSettlement:
    ativo: bool
    settlement_service: MissionRewardSettlementService | None
    gamification_service: GamificationService | None
    reconciliacao: ResultadoLiquidacaoLote | None
    erro: str | None


def criar_componentes_reward_settlement(
    *,
    caminho_banco: str | Path,
    user_identity_repository: UserIdentityRepository,
    mission_service: MissionService,
) -> tuple[
    MissionRewardSettlementService,
    GamificationService,
]:
    catalogo = criar_catalogo_missoes_producao_v1()

    ruleset = criar_ruleset_gamificacao_com_rewards_missoes_v1(catalogo)

    gamification_service = GamificationService(
        GamificationRepository(caminho_banco),
        user_identity_repository,
        ruleset,
    )

    settlement_service = MissionRewardSettlementService(
        mission_service=mission_service,
        gamification_service=gamification_service,
        catalogo=catalogo,
    )

    return (
        settlement_service,
        gamification_service,
    )


def ativar_reward_settlement_runtime(
    *,
    caminho_banco: str | Path,
    user_identity_repository: UserIdentityRepository,
    mission_service: MissionService,
    limite: int = 100,
) -> ResultadoAtivacaoRewardSettlement:
    try:
        (
            settlement_service,
            gamification_service,
        ) = criar_componentes_reward_settlement(
            caminho_banco=caminho_banco,
            user_identity_repository=(user_identity_repository),
            mission_service=mission_service,
        )

        reconciliacao = settlement_service.liquidar_pendentes(limite=limite)

        if reconciliacao.falhas:
            return ResultadoAtivacaoRewardSettlement(
                ativo=False,
                settlement_service=(settlement_service),
                gamification_service=(gamification_service),
                reconciliacao=(reconciliacao),
                erro=("settlement_incompleto:" + "|".join(reconciliacao.falhas)),
            )

        return ResultadoAtivacaoRewardSettlement(
            ativo=True,
            settlement_service=(settlement_service),
            gamification_service=(gamification_service),
            reconciliacao=reconciliacao,
            erro=None,
        )

    except Exception as exc:
        return ResultadoAtivacaoRewardSettlement(
            ativo=False,
            settlement_service=None,
            gamification_service=None,
            reconciliacao=None,
            erro=(f"{type(exc).__name__}: " f"{exc}"),
        )
