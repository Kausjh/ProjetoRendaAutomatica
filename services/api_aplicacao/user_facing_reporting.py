from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from models.community_moderation import (
    MOTIVOS_DENUNCIA_VALIDOS,
    DenunciaCommunityModeration,
)
from models.user_identity import ContaUsuario
from repositories.community_moderation_repository import (
    CommunityModerationRepository,
    ConflitoIdempotenciaCommunityModeration,
    ReporterCommunityModerationNaoEncontrado,
    TargetCommunityModerationNaoEncontrado,
)
from services.api_aplicacao.user_facing_http import (
    ErroHttpUserFacing,
)


class UserFacingCommunityReportingController:
    TARGET_TYPE = "community_discovery"

    CAMPOS_ACEITOS = frozenset(
        {
            "target_id",
            "motivo",
            "detalhes",
        }
    )

    def __init__(
        self,
        repository: CommunityModerationRepository | None,
        *,
        agora_provider: Callable[[], str] | None = None,
    ) -> None:
        self.repository = repository
        self._agora_provider = agora_provider

    def _repository(
        self,
    ) -> CommunityModerationRepository:
        if self.repository is None:
            raise ErroHttpUserFacing(
                503,
                "denuncias_comunitarias_indisponiveis",
                "Denuncias comunitarias indisponiveis.",
            )

        return self.repository

    def _agora(
        self,
    ) -> str:
        provider = self._agora_provider

        if provider is not None:
            return str(provider())

        return datetime.now(UTC).isoformat()

    @staticmethod
    def _serializar(
        denuncia: DenunciaCommunityModeration,
    ) -> dict[str, object]:
        return {
            "id": denuncia.id,
            "target_type": denuncia.target_type,
            "target_id": denuncia.target_id,
            "motivo": denuncia.motivo,
            "detalhes": denuncia.detalhes,
            "estado": denuncia.estado,
            "criado_em": denuncia.criado_em,
            "atualizado_em": denuncia.atualizado_em,
        }

    def criar(
        self,
        conta: ContaUsuario,
        payload: dict[str, object],
    ) -> tuple[int, dict[str, object]]:
        if not conta.ativa:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

        desconhecidos = set(payload) - self.CAMPOS_ACEITOS

        if desconhecidos:
            raise ErroHttpUserFacing(
                400,
                "payload_denuncia_invalido",
                ("O envio aceita somente " "target_id, motivo e detalhes."),
            )

        target_id = payload.get("target_id")

        if (
            not isinstance(
                target_id,
                str,
            )
            or not target_id.strip()
        ):
            raise ErroHttpUserFacing(
                400,
                "target_denuncia_invalido",
                "Informe target_id como texto nao vazio.",
            )

        motivo = payload.get("motivo")

        if (
            not isinstance(
                motivo,
                str,
            )
            or not motivo.strip()
        ):
            raise ErroHttpUserFacing(
                400,
                "motivo_denuncia_invalido",
                "Informe motivo como texto.",
            )

        motivo_normalizado = motivo.strip()

        if motivo_normalizado not in MOTIVOS_DENUNCIA_VALIDOS:
            raise ErroHttpUserFacing(
                400,
                "motivo_denuncia_invalido",
                "Motivo de denuncia invalido.",
            )

        detalhes = payload.get("detalhes")

        if detalhes is not None and not isinstance(
            detalhes,
            str,
        ):
            raise ErroHttpUserFacing(
                400,
                "detalhes_denuncia_invalidos",
                "detalhes precisa ser texto ou null.",
            )

        try:
            resultado = self._repository().registrar_denuncia(
                reporter_conta_id=conta.id,
                target_type=self.TARGET_TYPE,
                target_id=target_id.strip(),
                motivo=motivo_normalizado,
                detalhes=detalhes,
                agora=self._agora(),
            )

        except TargetCommunityModerationNaoEncontrado as erro:
            raise ErroHttpUserFacing(
                404,
                "target_denuncia_nao_encontrado",
                "Contribuicao comunitaria nao encontrada.",
            ) from erro

        except ReporterCommunityModerationNaoEncontrado as erro:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            ) from erro

        except ConflitoIdempotenciaCommunityModeration as erro:
            raise ErroHttpUserFacing(
                409,
                "conflito_denuncia",
                "A denuncia existente possui dados diferentes.",
            ) from erro

        except ValueError as erro:
            raise ErroHttpUserFacing(
                400,
                "denuncia_invalida",
                str(erro),
            ) from erro

        return (
            (201 if resultado.criado else 200),
            {
                "denuncia": (self._serializar(resultado.denuncia)),
                "criada": (resultado.criado),
            },
        )
