from __future__ import annotations

import hmac
import os
from dataclasses import dataclass

from dotenv import load_dotenv


class AutoridadeModeracaoIndisponivel(RuntimeError):
    pass


class AutorizacaoModeracaoNegada(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class ContextoAutoridadeModeracao:
    actor_id: str
    origem: str


class CommunityModerationAuthorityV1:
    ENV_TOKEN = "RADAR_ADMIN_TOKEN"

    ACTOR_ID = "radar-admin-control-plane-v1"

    ORIGEM = "admin_control_plane"

    def __init__(
        self,
        *,
        token_administrativo: str,
    ) -> None:
        token = str(token_administrativo or "").strip()

        if not token:
            raise (
                AutoridadeModeracaoIndisponivel(
                    "Moderacao autoritativa " "indisponivel sem " "RADAR_ADMIN_TOKEN."
                )
            )

        self._token_administrativo = token

    @classmethod
    def from_environment(
        cls,
    ) -> CommunityModerationAuthorityV1:
        load_dotenv()

        token = os.getenv(
            cls.ENV_TOKEN,
            "",
        ).strip()

        return cls(
            token_administrativo=token,
        )

    def autorizar(
        self,
        authorization_header: str | None,
    ) -> ContextoAutoridadeModeracao:
        header = str(authorization_header or "").strip()

        prefixo = "Bearer "

        token_recebido = header[len(prefixo) :].strip() if header.startswith(prefixo) else ""

        autorizado = bool(token_recebido) and hmac.compare_digest(
            token_recebido,
            self._token_administrativo,
        )

        if not autorizado:
            raise (AutorizacaoModeracaoNegada("Autoridade de moderacao " "nao autorizada."))

        return ContextoAutoridadeModeracao(
            actor_id=self.ACTOR_ID,
            origem=self.ORIGEM,
        )
