from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from models.mission_community import (
    ResultadoReconciliacaoMissoes,
)
from repositories.mission_community_reconciliation_repository import (
    MissionCommunityReconciliationRepository,
)
from repositories.mission_repository import (
    MissionRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.mission_community_approved_wiring import (
    MissionCommunityApprovedWiring,
)
from services.mission_community_reconciliation_service import (
    MissionCommunityReconciliationService,
)
from services.mission_production_catalog import (
    criar_catalogo_missoes_producao_v1,
)
from services.mission_service import (
    MissionService,
)


@dataclass(frozen=True, slots=True)
class ResultadoAtivacaoMissoes:
    ativo: bool
    service: MissionService | None
    wiring: MissionCommunityApprovedWiring | None
    reconciliacao: ResultadoReconciliacaoMissoes | None
    erro: str | None


def _criar_service_e_wiring(
    *,
    caminho_banco: str | Path,
    user_identity_repository: UserIdentityRepository,
) -> tuple[
    MissionService,
    MissionCommunityApprovedWiring,
]:
    catalogo = criar_catalogo_missoes_producao_v1()

    mission_repository = MissionRepository(caminho_banco)

    mission_service = MissionService(
        repository=mission_repository,
        identity_repository=(user_identity_repository),
        ruleset=catalogo.ruleset,
    )

    wiring = MissionCommunityApprovedWiring(
        mission_service=mission_service,
        catalogo=catalogo,
    )

    return (
        mission_service,
        wiring,
    )


def criar_wiring_missoes_live(
    *,
    caminho_banco: str | Path,
) -> MissionCommunityApprovedWiring:
    identity_repository = UserIdentityRepository(caminho_banco)

    _, wiring = _criar_service_e_wiring(
        caminho_banco=caminho_banco,
        user_identity_repository=(identity_repository),
    )

    return wiring


def ativar_missoes_runtime(
    *,
    caminho_banco: str | Path,
    user_identity_repository: UserIdentityRepository,
) -> ResultadoAtivacaoMissoes:
    try:
        (
            mission_service,
            wiring,
        ) = _criar_service_e_wiring(
            caminho_banco=caminho_banco,
            user_identity_repository=(user_identity_repository),
        )

        reconciliation_repository = MissionCommunityReconciliationRepository(caminho_banco)

        reconciliation_service = MissionCommunityReconciliationService(
            repository=(reconciliation_repository),
            wiring=wiring,
        )

        reconciliacao = reconciliation_service.reconciliar()

        if not reconciliacao.sucesso:
            return ResultadoAtivacaoMissoes(
                ativo=False,
                service=None,
                wiring=None,
                reconciliacao=reconciliacao,
                erro="reconciliacao_incompleta",
            )

        return ResultadoAtivacaoMissoes(
            ativo=True,
            service=mission_service,
            wiring=wiring,
            reconciliacao=reconciliacao,
            erro=None,
        )

    except Exception as exc:
        return ResultadoAtivacaoMissoes(
            ativo=False,
            service=None,
            wiring=None,
            reconciliacao=None,
            erro=(f"{type(exc).__name__}: " f"{exc}"),
        )
