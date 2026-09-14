from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, BinaryIO, Protocol

from models.user_identity import ContaUsuario

if TYPE_CHECKING:
    from services.user_identity_service import UserIdentityService

API_VERSION = "v1"
USER_SESSION_HEADER = "X-User-Session"
USER_SESSION_TOKEN_PREFIX = "pra_usr_v1_"
DEFAULT_MAX_JSON_BODY_BYTES = 64 * 1024
MAX_USER_SESSION_TOKEN_LENGTH = 512


class HeadersLike(Protocol):
    def get(
        self,
        name: str,
        default: str | None = None,
    ) -> str | None: ...


@dataclass(frozen=True, slots=True)
class ErroHttpUserFacing(Exception):
    status: int
    codigo: str
    mensagem: str

    def __post_init__(self) -> None:
        Exception.__init__(self, self.mensagem)

    def payload(self) -> dict[str, object]:
        return {
            "api_version": API_VERSION,
            "erro": {
                "codigo": self.codigo,
                "mensagem": self.mensagem,
            },
        }


class UserFacingHttpFoundation:
    def __init__(
        self,
        *,
        user_identity_service: UserIdentityService | None = None,
        max_json_body_bytes: int = DEFAULT_MAX_JSON_BODY_BYTES,
    ) -> None:
        if max_json_body_bytes <= 0:
            raise ValueError("max_json_body_bytes precisa ser positivo.")

        self.user_identity_service = user_identity_service
        self.max_json_body_bytes = int(max_json_body_bytes)

    @staticmethod
    def sucesso(dados: object) -> dict[str, object]:
        return {
            "api_version": API_VERSION,
            "dados": dados,
        }

    @staticmethod
    def _content_type_json(headers: HeadersLike) -> bool:
        valor = str(headers.get("Content-Type", "") or "")
        media_type = valor.split(";", 1)[0].strip().lower()
        return media_type == "application/json"

    def ler_json_objeto(
        self,
        *,
        headers: HeadersLike,
        stream: BinaryIO,
    ) -> dict[str, object]:
        if not self._content_type_json(headers):
            raise ErroHttpUserFacing(
                415,
                "content_type_invalido",
                "Content-Type deve ser application/json.",
            )

        bruto_tamanho = str(headers.get("Content-Length", "") or "").strip()
        if not bruto_tamanho:
            raise ErroHttpUserFacing(
                400,
                "content_length_ausente",
                "Content-Length e obrigatorio para este payload.",
            )

        try:
            tamanho = int(bruto_tamanho)
        except ValueError as erro:
            raise ErroHttpUserFacing(
                400,
                "content_length_invalido",
                "Content-Length invalido.",
            ) from erro

        if tamanho <= 0:
            raise ErroHttpUserFacing(
                400,
                "payload_vazio",
                "O corpo JSON nao pode ser vazio.",
            )

        if tamanho > self.max_json_body_bytes:
            raise ErroHttpUserFacing(
                413,
                "payload_muito_grande",
                "O corpo JSON excede o limite permitido.",
            )

        corpo = stream.read(tamanho)
        if len(corpo) != tamanho:
            raise ErroHttpUserFacing(
                400,
                "payload_incompleto",
                "O corpo recebido esta incompleto.",
            )

        try:
            texto = corpo.decode("utf-8")
        except UnicodeDecodeError as erro:
            raise ErroHttpUserFacing(
                400,
                "json_utf8_invalido",
                "O corpo JSON precisa usar UTF-8 valido.",
            ) from erro

        try:
            payload = json.loads(texto)
        except json.JSONDecodeError as erro:
            raise ErroHttpUserFacing(
                400,
                "json_invalido",
                "O corpo nao contem JSON valido.",
            ) from erro

        if not isinstance(payload, dict):
            raise ErroHttpUserFacing(
                400,
                "json_objeto_obrigatorio",
                "O corpo JSON precisa ser um objeto.",
            )

        return payload

    @staticmethod
    def extrair_token_sessao(
        headers: HeadersLike,
        *,
        obrigatorio: bool = False,
    ) -> str | None:
        valor = str(headers.get(USER_SESSION_HEADER, "") or "").strip()

        if not valor:
            if obrigatorio:
                raise ErroHttpUserFacing(
                    401,
                    "sessao_usuario_obrigatoria",
                    "Sessao de usuario obrigatoria.",
                )
            return None

        if len(valor) > MAX_USER_SESSION_TOKEN_LENGTH or not valor.startswith(
            USER_SESSION_TOKEN_PREFIX
        ):
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

        return valor

    def resolver_usuario(
        self,
        headers: HeadersLike,
    ) -> ContaUsuario:
        token = self.extrair_token_sessao(
            headers,
            obrigatorio=True,
        )
        assert token is not None

        service = self.user_identity_service
        if service is None:
            raise ErroHttpUserFacing(
                503,
                "identidade_usuario_indisponivel",
                "Identidade de usuario indisponivel.",
            )

        conta = service.resolver_sessao(token)
        if conta is None:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

        return conta
