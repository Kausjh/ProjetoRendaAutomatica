from __future__ import annotations

from pathlib import Path

from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
)
from services.community_trust_discovery_wiring import (
    CommunityTrustDiscoveryWiring,
)
from services.community_trust_terminal_hook import (
    CommunityTrustTerminalHook,
)


def criar_terminal_hook_community_trust_live(
    *,
    caminho_banco: str | Path,
    discovery_repository: CommunityDiscoveryRepository,
) -> CommunityTrustTerminalHook:
    trust_repository = CommunityTrustRepository(caminho_banco)

    trust_wiring = CommunityTrustDiscoveryWiring(trust_repository)

    return CommunityTrustTerminalHook(
        discovery_repository,
        trust_wiring,
    )
