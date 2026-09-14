from __future__ import annotations

from models.user_identity import ContaUsuario, DispositivoUsuario
from services.api_aplicacao.user_facing_http import ErroHttpUserFacing
from services.user_identity_service import UserIdentityService


class UserFacingDevicesController:
    CAMPOS_PERMITIDOS = frozenset({"plataforma", "push_token"})

    def __init__(self, user_identity_service: UserIdentityService | None) -> None:
        self.user_identity_service = user_identity_service

    def _service(self) -> UserIdentityService:
        service = self.user_identity_service
        if service is None:
            raise ErroHttpUserFacing(
                503,
                "identidade_usuario_indisponivel",
                "Identidade de usuario indisponivel.",
            )
        return service

    @staticmethod
    def _serializar(dispositivo: DispositivoUsuario) -> dict[str, object]:
        return {
            "id": dispositivo.id,
            "instalacao_id": dispositivo.instalacao_id,
            "plataforma": dispositivo.plataforma,
            "ativo": dispositivo.ativo,
            "criado_em": dispositivo.criado_em,
            "atualizado_em": dispositivo.atualizado_em,
            "revogado_em": dispositivo.revogado_em,
        }

    @staticmethod
    def _traduzir_erro(erro: ValueError) -> ErroHttpUserFacing:
        mensagem = str(erro)

        if "outra instalacao" in mensagem:
            return ErroHttpUserFacing(
                409,
                "token_dispositivo_em_uso",
                "Token de dispositivo ja associado a outra instalacao.",
            )

        return ErroHttpUserFacing(
            400,
            "dispositivo_invalido",
            mensagem,
        )

    def listar(
        self,
        conta: ContaUsuario,
    ) -> tuple[int, dict[str, object]]:
        dispositivos = self._service().listar_dispositivos(conta.id)
        return (
            200,
            {
                "dispositivos": [self._serializar(dispositivo) for dispositivo in dispositivos],
            },
        )

    def salvar(
        self,
        conta: ContaUsuario,
        instalacao_id: str,
        payload: dict[str, object],
    ) -> tuple[int, dict[str, object]]:
        desconhecidos = set(payload) - self.CAMPOS_PERMITIDOS
        if desconhecidos:
            raise ErroHttpUserFacing(
                400,
                "payload_invalido",
                "Payload contem campos nao permitidos.",
            )

        plataforma = payload.get("plataforma")
        push_token = payload.get("push_token")

        if not isinstance(plataforma, str) or not isinstance(push_token, str):
            raise ErroHttpUserFacing(
                400,
                "payload_invalido",
                "plataforma e push_token sao obrigatorios.",
            )

        try:
            dispositivo, criado, token_rotacionado = self._service().registrar_dispositivo(
                conta_id=conta.id,
                instalacao_id=instalacao_id,
                plataforma=plataforma,
                push_token=push_token,
            )
        except ValueError as erro:
            raise self._traduzir_erro(erro) from erro

        return (
            201 if criado else 200,
            {
                "dispositivo": self._serializar(dispositivo),
                "criado": criado,
                "token_rotacionado": token_rotacionado,
            },
        )

    def remover(
        self,
        conta: ContaUsuario,
        instalacao_id: str,
    ) -> tuple[int, dict[str, object]]:
        try:
            dispositivo = self._service().revogar_dispositivo(
                conta_id=conta.id,
                instalacao_id=instalacao_id,
            )
        except ValueError as erro:
            raise self._traduzir_erro(erro) from erro

        if dispositivo is None:
            raise ErroHttpUserFacing(
                404,
                "dispositivo_nao_encontrado",
                "Dispositivo nao encontrado.",
            )

        return (
            200,
            {
                "dispositivo": self._serializar(dispositivo),
                "revogado": True,
            },
        )
