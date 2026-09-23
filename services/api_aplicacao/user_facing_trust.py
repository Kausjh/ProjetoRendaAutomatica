from __future__ import annotations

from models.user_identity import (
    ContaUsuario,
)
from services.api_aplicacao.user_facing_http import (
    ErroHttpUserFacing,
)
from services.community_trust_read_service import (
    CommunityTrustReadService,
    LeituraCommunityTrustUsuario,
)


class UserFacingCommunityTrustController:
    def __init__(
        self,
        read_service: CommunityTrustReadService | None,
    ) -> None:
        self.read_service = read_service

    def _service(
        self,
    ) -> CommunityTrustReadService:
        service = self.read_service

        if service is None:
            raise ErroHttpUserFacing(
                503,
                "trust_comunitario_indisponivel",
                "Trust comunitario indisponivel.",
            )

        return service

    @staticmethod
    def _validar_conta(
        conta: ContaUsuario,
    ) -> None:
        if not conta.ativa:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

    @staticmethod
    def _serializar(
        leitura: LeituraCommunityTrustUsuario,
    ) -> dict[str, object]:
        perfil = leitura.perfil

        return {
            "perfil": {
                "evidencias_total": int(perfil.evidencias_total),
                "positivas_total": int(perfil.positivas_total),
                "negativas_total": int(perfil.negativas_total),
                "neutras_total": int(perfil.neutras_total),
                "atualizado_em": perfil.atualizado_em,
            },
            "modelo": {
                "versao": int(leitura.read_model_version),
                "score_numerico_definido": False,
            },
        }

    def obter(
        self,
        conta: ContaUsuario,
    ) -> tuple[
        int,
        dict[str, object],
    ]:
        self._validar_conta(conta)

        try:
            leitura = self._service().obter(conta.id)

        except ValueError as erro:
            raise ErroHttpUserFacing(
                400,
                "trust_comunitario_invalido",
                "Leitura de Trust invalida.",
            ) from erro

        return (
            200,
            self._serializar(leitura),
        )
