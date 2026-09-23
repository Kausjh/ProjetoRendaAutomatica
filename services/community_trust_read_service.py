from __future__ import annotations

from dataclasses import dataclass

from models.community_trust import (
    PerfilCommunityTrust,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
)

PUBLIC_TRUST_READ_MODEL_VERSION = 1


@dataclass(frozen=True, slots=True)
class LeituraCommunityTrustUsuario:
    perfil: PerfilCommunityTrust
    read_model_version: int


class CommunityTrustReadService:
    def __init__(
        self,
        repository: CommunityTrustRepository,
    ) -> None:
        self.repository = repository

    def obter(
        self,
        conta_id: str,
    ) -> LeituraCommunityTrustUsuario:
        conta = str(conta_id or "").strip()

        if not conta:
            raise ValueError("conta_id e obrigatorio.")

        perfil = self.repository.obter_perfil(conta)

        return LeituraCommunityTrustUsuario(
            perfil=perfil,
            read_model_version=(PUBLIC_TRUST_READ_MODEL_VERSION),
        )
