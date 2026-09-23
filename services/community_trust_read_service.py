from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Protocol

from models.community_trust import (
    PerfilCommunityTrust,
)

PUBLIC_TRUST_READ_MODEL_VERSION = 1


class CommunityTrustProfileReader(Protocol):
    def obter_perfil(
        self,
        conta_id: str,
    ) -> PerfilCommunityTrust: ...


class CommunityTrustReadUnavailableError(RuntimeError):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class LeituraCommunityTrustUsuario:
    perfil: PerfilCommunityTrust
    read_model_version: int


class CommunityTrustReadService:
    def __init__(
        self,
        repository: CommunityTrustProfileReader,
    ) -> None:
        self.repository = repository

    def obter(
        self,
        conta_id: str,
    ) -> LeituraCommunityTrustUsuario:
        conta = str(conta_id or "").strip()

        if not conta:
            raise ValueError("conta_id e obrigatorio.")

        try:
            perfil = self.repository.obter_perfil(conta)

        except sqlite3.Error as erro:
            raise (
                CommunityTrustReadUnavailableError("Leitura de Community Trust indisponivel.")
            ) from erro

        return LeituraCommunityTrustUsuario(
            perfil=perfil,
            read_model_version=(PUBLIC_TRUST_READ_MODEL_VERSION),
        )
