from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from repositories.gamification_reconciliation_repository import (
    GamificationReconciliationRepository,
)
from repositories.gamification_repository import (
    GamificationRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)
from services.gamification_event_wiring import (
    GamificationEventWiring,
)
from services.gamification_production_rules import (
    criar_ruleset_producao_v1,
)
from services.gamification_reconciliation_service import (
    GamificationReconciliationService,
    ResultadoReconciliacaoGamificacao,
)
from services.gamification_service import (
    GamificationService,
)
from services.user_identity_service import (
    UserIdentityService,
)
from services.user_personalization_service import (
    UserPersonalizationService,
)


@dataclass(frozen=True, slots=True)
class ResultadoAtivacaoGamificacao:
    ativo: bool
    service: GamificationService | None
    reconciliacao: ResultadoReconciliacaoGamificacao | None
    erro: str | None


def ativar_gamificacao_runtime(
    *,
    caminho_banco: str | Path,
    user_identity_repository: UserIdentityRepository,
    user_identity_service: UserIdentityService,
    user_personalization_repository: UserPersonalizationRepository,
    user_personalization_service: UserPersonalizationService,
) -> ResultadoAtivacaoGamificacao:
    try:
        gamification_repository = GamificationRepository(caminho_banco)

        gamification_service = GamificationService(
            repository=(gamification_repository),
            identity_repository=(user_identity_repository),
            ruleset=(criar_ruleset_producao_v1()),
        )

        wiring = GamificationEventWiring(gamification_service)

        reconciliation_repository = GamificationReconciliationRepository(caminho_banco)

        reconciliation_service = GamificationReconciliationService(
            repository=(reconciliation_repository),
            wiring=wiring,
        )

        reconciliacao = reconciliation_service.reconciliar()

        if not reconciliacao.sucesso:
            return ResultadoAtivacaoGamificacao(
                ativo=False,
                service=None,
                reconciliacao=reconciliacao,
                erro=("reconciliacao_incompleta"),
            )

        user_identity_service.configurar_gamificacao(wiring)

        user_personalization_service.configurar_gamificacao(wiring)

        return ResultadoAtivacaoGamificacao(
            ativo=True,
            service=gamification_service,
            reconciliacao=reconciliacao,
            erro=None,
        )

    except Exception as exc:
        return ResultadoAtivacaoGamificacao(
            ativo=False,
            service=None,
            reconciliacao=None,
            erro=(f"{type(exc).__name__}: " f"{exc}"),
        )
