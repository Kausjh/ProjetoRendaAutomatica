from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.community_moderation_repository import (
    CommunityModerationRepository,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
)
from services.community_moderation_authority import (
    CommunityModerationAuthorityV1,
)
from services.community_moderation_service import (
    CommunityModerationService,
)
from services.community_moderation_trust_bridge import (
    CommunityModerationTrustBridge,
)
from services.community_moderation_trust_reconciliation import (
    CommunityModerationTrustReconciliation,
    ResultadoReconciliacaoModerationTrust,
)

RUNTIME_FLAG = "COMMUNITY_MODERATION_RUNTIME_ATIVO"

RECONCILIATION_STARTUP_FLAG = "COMMUNITY_MODERATION_" "RECONCILIATION_STARTUP_ATIVA"


def _flag_ativo(
    nome: str,
) -> bool:
    valor = (
        os.getenv(
            nome,
            "",
        )
        .strip()
        .casefold()
    )

    return valor in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass(frozen=True, slots=True)
class ComponentesCommunityModerationRuntime:
    moderation_repository: CommunityModerationRepository
    discovery_repository: CommunityDiscoveryRepository
    trust_repository: CommunityTrustRepository
    authority: CommunityModerationAuthorityV1
    trust_bridge: CommunityModerationTrustBridge
    moderation_service: CommunityModerationService
    reconciliation_service: CommunityModerationTrustReconciliation


@dataclass(frozen=True, slots=True)
class ResultadoAtivacaoCommunityModeration:
    ativo: bool
    componentes: ComponentesCommunityModerationRuntime | None
    reconciliacao: ResultadoReconciliacaoModerationTrust | None
    erro: str | None
    schema_activation_autorizada: bool
    reconciliation_executada: bool


def _criar_componentes(
    *,
    caminho_banco: str | Path,
    authority: CommunityModerationAuthorityV1 | None,
) -> ComponentesCommunityModerationRuntime:
    # A autoridade e resolvida ANTES de qualquer
    # repository que possa garantir/criar schema.
    authority_final = (
        authority if authority is not None else (CommunityModerationAuthorityV1.from_environment())
    )

    moderation_repository = CommunityModerationRepository(caminho_banco)

    discovery_repository = CommunityDiscoveryRepository(caminho_banco)

    trust_repository = CommunityTrustRepository(caminho_banco)

    trust_bridge = CommunityModerationTrustBridge(
        discovery_repository=(discovery_repository),
        trust_repository=(trust_repository),
    )

    moderation_service = CommunityModerationService(
        repository=(moderation_repository),
        authority=authority_final,
        trust_bridge=trust_bridge,
    )

    reconciliation_service = CommunityModerationTrustReconciliation(
        moderation_repository=(moderation_repository),
        trust_bridge=trust_bridge,
    )

    return ComponentesCommunityModerationRuntime(
        moderation_repository=(moderation_repository),
        discovery_repository=(discovery_repository),
        trust_repository=(trust_repository),
        authority=authority_final,
        trust_bridge=trust_bridge,
        moderation_service=(moderation_service),
        reconciliation_service=(reconciliation_service),
    )


def ativar_community_moderation_runtime(
    *,
    caminho_banco: str | Path,
    permitir_schema_activation: bool = False,
    authority: CommunityModerationAuthorityV1 | None = None,
    executar_reconciliation: bool | None = None,
    limite_reconciliation: int = 100,
) -> ResultadoAtivacaoCommunityModeration:
    if not _flag_ativo(RUNTIME_FLAG):
        return ResultadoAtivacaoCommunityModeration(
            ativo=False,
            componentes=None,
            reconciliacao=None,
            erro="feature_flag_disabled",
            schema_activation_autorizada=False,
            reconciliation_executada=False,
        )

    if not permitir_schema_activation:
        return ResultadoAtivacaoCommunityModeration(
            ativo=False,
            componentes=None,
            reconciliacao=None,
            erro=("schema_activation_not_authorized"),
            schema_activation_autorizada=False,
            reconciliation_executada=False,
        )

    try:
        componentes = _criar_componentes(
            caminho_banco=caminho_banco,
            authority=authority,
        )

        executar = (
            _flag_ativo(RECONCILIATION_STARTUP_FLAG)
            if executar_reconciliation is None
            else bool(executar_reconciliation)
        )

        reconciliacao = None

        if executar:
            reconciliacao = componentes.reconciliation_service.reconciliar(
                limite=(limite_reconciliation)
            )

            if reconciliacao.falhas:
                return ResultadoAtivacaoCommunityModeration(
                    ativo=False,
                    componentes=None,
                    reconciliacao=(reconciliacao),
                    erro=("reconciliacao_incompleta:" f"{len(reconciliacao.falhas)}"),
                    schema_activation_autorizada=True,
                    reconciliation_executada=True,
                )

        return ResultadoAtivacaoCommunityModeration(
            ativo=True,
            componentes=componentes,
            reconciliacao=reconciliacao,
            erro=None,
            schema_activation_autorizada=True,
            reconciliation_executada=executar,
        )

    except Exception as exc:
        return ResultadoAtivacaoCommunityModeration(
            ativo=False,
            componentes=None,
            reconciliacao=None,
            erro=(f"{type(exc).__name__}: " f"{exc}"),
            schema_activation_autorizada=True,
            reconciliation_executada=False,
        )
