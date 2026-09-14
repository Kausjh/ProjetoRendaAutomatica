from __future__ import annotations

from models.user_identity import ContaUsuario
from services.api_aplicacao.user_facing_http import ErroHttpUserFacing
from services.user_identity_service import UserIdentityService


class UserFacingAuthController:
    def __init__(
        self,
        user_identity_service: UserIdentityService | None,
    ) -> None:
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
    def _campo_texto(
        payload: dict[str, object],
        nome: str,
    ) -> str:
        valor = payload.get(nome)
        if not isinstance(valor, str) or not valor.strip():
            raise ErroHttpUserFacing(
                400,
                "payload_invalido",
                f"Campo obrigatorio invalido: {nome}.",
            )
        return valor

    @staticmethod
    def conta_publica(
        conta: ContaUsuario,
    ) -> dict[str, object]:
        return {
            "id": conta.id,
            "email": conta.email,
            "criado_em": conta.criado_em,
            "ativa": conta.ativa,
        }

    def registrar(
        self,
        payload: dict[str, object],
    ) -> tuple[int, dict[str, object]]:
        email = self._campo_texto(payload, "email")
        senha = self._campo_texto(payload, "senha")

        try:
            conta = self._service().criar_conta(
                email=email,
                senha=senha,
            )
        except ValueError as erro:
            mensagem = str(erro)

            if "Ja existe uma conta para este email." in mensagem:
                raise ErroHttpUserFacing(
                    409,
                    "email_em_uso",
                    "Email ja cadastrado.",
                ) from erro

            raise ErroHttpUserFacing(
                400,
                "cadastro_invalido",
                mensagem,
            ) from erro

        return (
            201,
            {
                "conta": self.conta_publica(conta),
            },
        )

    def login(
        self,
        payload: dict[str, object],
    ) -> tuple[int, dict[str, object]]:
        email = self._campo_texto(payload, "email")
        senha = self._campo_texto(payload, "senha")

        try:
            emitida = self._service().autenticar_e_emitir_sessao(
                email=email,
                senha=senha,
            )
        except ValueError:
            emitida = None

        if emitida is None:
            raise ErroHttpUserFacing(
                401,
                "credenciais_invalidas",
                "Credenciais invalidas.",
            )

        return (
            200,
            {
                "conta": self.conta_publica(emitida.conta),
                "sessao": {
                    "token": emitida.token,
                    "expira_em": emitida.sessao.expira_em,
                },
            },
        )

    def me(
        self,
        conta: ContaUsuario,
    ) -> tuple[int, dict[str, object]]:
        return (
            200,
            {
                "conta": self.conta_publica(conta),
            },
        )

    def logout(
        self,
        token: str,
    ) -> tuple[int, dict[str, object]]:
        if not self._service().revogar_sessao(token):
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

        return (
            200,
            {
                "sessao_revogada": True,
            },
        )
