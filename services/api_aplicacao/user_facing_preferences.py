from __future__ import annotations

from models.user_identity import ContaUsuario
from models.user_personalization import PreferenciasUsuario
from services.api_aplicacao.user_facing_http import ErroHttpUserFacing
from services.user_personalization_service import UserPersonalizationService


class UserFacingPreferencesController:
    CAMPOS_PERMITIDOS = frozenset(
        {
            "notificacoes_preco_habilitadas",
            "marketplaces_preferidos",
        }
    )

    def __init__(
        self,
        user_personalization_service: UserPersonalizationService | None,
    ) -> None:
        self.user_personalization_service = user_personalization_service

    def _service(self) -> UserPersonalizationService:
        service = self.user_personalization_service
        if service is None:
            raise ErroHttpUserFacing(
                503,
                "personalizacao_indisponivel",
                "Personalizacao de usuario indisponivel.",
            )
        return service

    @staticmethod
    def _serializar(
        preferencias: PreferenciasUsuario,
    ) -> dict[str, object]:
        return {
            "notificacoes_preco_habilitadas": (preferencias.notificacoes_preco_habilitadas),
            "marketplaces_preferidos": list(preferencias.marketplaces_preferidos),
            "atualizado_em": preferencias.atualizado_em,
        }

    @staticmethod
    def _traduzir_erro_service(
        erro: ValueError,
    ) -> ErroHttpUserFacing:
        mensagem = str(erro)

        if "Conta inexistente ou inativa." in mensagem:
            return ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

        return ErroHttpUserFacing(
            400,
            "preferencias_invalidas",
            mensagem,
        )

    def obter(
        self,
        conta: ContaUsuario,
    ) -> tuple[int, dict[str, object]]:
        try:
            preferencias = self._service().obter_preferencias(conta.id)
        except ValueError as erro:
            raise self._traduzir_erro_service(erro) from erro

        return 200, {"preferencias": self._serializar(preferencias)}

    def atualizar(
        self,
        conta: ContaUsuario,
        payload: dict[str, object],
    ) -> tuple[int, dict[str, object]]:
        desconhecidos = set(payload) - self.CAMPOS_PERMITIDOS
        if desconhecidos:
            raise ErroHttpUserFacing(
                400,
                "payload_invalido",
                "Payload contem campos nao permitidos.",
            )

        if not payload:
            raise ErroHttpUserFacing(
                400,
                "payload_invalido",
                "Informe ao menos uma preferencia para atualizar.",
            )

        try:
            atuais = self._service().obter_preferencias(conta.id)
        except ValueError as erro:
            raise self._traduzir_erro_service(erro) from erro

        notificacoes = payload.get(
            "notificacoes_preco_habilitadas",
            atuais.notificacoes_preco_habilitadas,
        )
        marketplaces = payload.get(
            "marketplaces_preferidos",
            list(atuais.marketplaces_preferidos),
        )

        if not isinstance(notificacoes, bool):
            raise ErroHttpUserFacing(
                400,
                "payload_invalido",
                "notificacoes_preco_habilitadas precisa ser booleano.",
            )

        if not isinstance(marketplaces, list) or not all(
            isinstance(item, str) for item in marketplaces
        ):
            raise ErroHttpUserFacing(
                400,
                "payload_invalido",
                "marketplaces_preferidos precisa ser uma lista de strings.",
            )

        try:
            preferencias = self._service().atualizar_preferencias(
                conta_id=conta.id,
                notificacoes_preco_habilitadas=notificacoes,
                marketplaces_preferidos=marketplaces,
            )
        except ValueError as erro:
            raise self._traduzir_erro_service(erro) from erro

        return 200, {"preferencias": self._serializar(preferencias)}
