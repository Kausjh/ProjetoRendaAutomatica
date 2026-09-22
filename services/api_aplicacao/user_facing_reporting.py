from __future__ import annotations

import re
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
    DuplicataDenunciaCommunityModeration,
    ReporterCommunityModerationNaoEncontrado,
    TargetCommunityModerationNaoEncontrado,
)
from services.api_aplicacao.user_facing_http import (
    ErroHttpUserFacing,
)


class UserFacingCommunityReportingController:
    TARGET_TYPE = "community_discovery"
    IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

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

    @staticmethod
    def _serializar_status(
        denuncia: DenunciaCommunityModeration,
    ) -> dict[str, object]:
        return {
            "id": denuncia.id,
            "target_type": denuncia.target_type,
            "target_id": denuncia.target_id,
            "motivo": denuncia.motivo,
            "estado": denuncia.estado,
            "criado_em": denuncia.criado_em,
            "atualizado_em": denuncia.atualizado_em,
        }

    @classmethod
    def _serializar_detalhe(
        cls,
        denuncia: DenunciaCommunityModeration,
    ) -> dict[str, object]:
        dados = cls._serializar_status(denuncia)

        dados["detalhes"] = denuncia.detalhes

        return dados

    @staticmethod
    def _paginacao_readback(
        *,
        limite: object,
        offset: object,
    ) -> tuple[int, int]:
        try:
            limite_int = int(str(limite).strip())

            offset_int = int(str(offset).strip())

        except (
            TypeError,
            ValueError,
        ) as erro:
            raise ErroHttpUserFacing(
                400,
                "paginacao_denuncias_invalida",
                "Paginacao de denuncias invalida.",
            ) from erro

        if limite_int < 1 or limite_int > 100 or offset_int < 0:
            raise ErroHttpUserFacing(
                400,
                "paginacao_denuncias_invalida",
                ("limite deve estar entre 1 e 100 " "e offset deve ser maior ou igual a zero."),
            )

        return (
            limite_int,
            offset_int,
        )

    def listar_status(
        self,
        conta: ContaUsuario,
        *,
        limite: object = "20",
        offset: object = "0",
    ) -> tuple[int, dict[str, object]]:
        if not conta.ativa:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

        limite_int, offset_int = self._paginacao_readback(
            limite=limite,
            offset=offset,
        )

        denuncias = self._repository().listar_denuncias_reporter(
            reporter_conta_id=conta.id,
            limite=limite_int,
            offset=offset_int,
        )

        itens = [self._serializar_status(denuncia) for denuncia in denuncias]

        return (
            200,
            {
                "itens": itens,
                "limite": limite_int,
                "offset": offset_int,
                "quantidade": len(itens),
            },
        )

    def obter_status(
        self,
        conta: ContaUsuario,
        denuncia_id: object,
    ) -> tuple[int, dict[str, object]]:
        if not conta.ativa:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

        identificador = str(denuncia_id if denuncia_id is not None else "").strip()

        if not identificador:
            raise ErroHttpUserFacing(
                404,
                "denuncia_nao_encontrada",
                "Denuncia nao encontrada.",
            )

        denuncia = self._repository().obter_denuncia_reporter(
            denuncia_id=identificador,
            reporter_conta_id=conta.id,
        )

        if denuncia is None:
            raise ErroHttpUserFacing(
                404,
                "denuncia_nao_encontrada",
                "Denuncia nao encontrada.",
            )

        return (
            200,
            {
                "denuncia": (self._serializar_detalhe(denuncia)),
            },
        )

    def criar_idempotente(
        self,
        conta: ContaUsuario,
        payload: dict[str, object],
        *,
        idempotency_key: object | None,
    ) -> tuple[int, dict[str, object]]:
        if not conta.ativa:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

        chave = str(idempotency_key if idempotency_key is not None else "").strip()

        if not chave:
            raise ErroHttpUserFacing(
                400,
                "idempotency_key_obrigatoria",
                "Idempotency-Key e obrigatoria.",
            )

        if not self.IDEMPOTENCY_KEY_PATTERN.fullmatch(chave):
            raise ErroHttpUserFacing(
                400,
                "idempotency_key_invalida",
                ("Idempotency-Key deve conter de 1 a " "128 caracteres seguros."),
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
            resultado = self._repository().registrar_denuncia_usuario(
                reporter_conta_id=conta.id,
                target_type=self.TARGET_TYPE,
                target_id=target_id.strip(),
                motivo=motivo_normalizado,
                detalhes=detalhes,
                acao_idempotencia=chave,
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
                "idempotency_key_reutilizada",
                ("Idempotency-Key ja foi utilizada " "com outro payload."),
            ) from erro

        except DuplicataDenunciaCommunityModeration as erro:
            raise ErroHttpUserFacing(
                409,
                "denuncia_duplicada",
                ("Uma denuncia equivalente ja existe " "para este usuario."),
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
                "idempotent_replay": (not resultado.criado),
            },
        )

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
