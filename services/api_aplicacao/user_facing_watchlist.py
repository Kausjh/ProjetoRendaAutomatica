from __future__ import annotations

from models.user_identity import ContaUsuario
from models.user_personalization import ItemWatchlistUsuario
from services.api_aplicacao.user_facing_http import ErroHttpUserFacing
from services.user_personalization_service import UserPersonalizationService


class UserFacingWatchlistController:
    CAMPOS_PERMITIDOS = frozenset(
        {
            "preco_alvo",
            "notificar_queda_preco",
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
        item: ItemWatchlistUsuario,
    ) -> dict[str, object]:
        return {
            "canonical_key": item.canonical_key,
            "preco_alvo": (format(item.preco_alvo, ".2f") if item.preco_alvo is not None else None),
            "notificar_queda_preco": item.notificar_queda_preco,
            "criado_em": item.criado_em,
            "atualizado_em": item.atualizado_em,
        }

    @staticmethod
    def _traduzir_erro(
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
            "watchlist_invalida",
            mensagem,
        )

    def listar(
        self,
        conta: ContaUsuario,
    ) -> tuple[int, dict[str, object]]:
        try:
            itens = self._service().listar_watchlist(conta.id)
        except ValueError as erro:
            raise self._traduzir_erro(erro) from erro

        return (
            200,
            {
                "itens": [self._serializar(item) for item in itens],
            },
        )

    def salvar(
        self,
        conta: ContaUsuario,
        canonical_key: str,
        payload: dict[str, object],
    ) -> tuple[int, dict[str, object]]:
        desconhecidos = set(payload) - self.CAMPOS_PERMITIDOS
        if desconhecidos:
            raise ErroHttpUserFacing(
                400,
                "payload_invalido",
                "Payload contem campos nao permitidos.",
            )

        preco_alvo = payload.get("preco_alvo")
        if isinstance(preco_alvo, bool) or not (
            preco_alvo is None or isinstance(preco_alvo, (str, int, float))
        ):
            raise ErroHttpUserFacing(
                400,
                "payload_invalido",
                "preco_alvo precisa ser numero, string numerica ou null.",
            )

        notificar = payload.get("notificar_queda_preco", True)
        if not isinstance(notificar, bool):
            raise ErroHttpUserFacing(
                400,
                "payload_invalido",
                "notificar_queda_preco precisa ser booleano.",
            )

        try:
            item = self._service().adicionar_ou_atualizar_watchlist(
                conta_id=conta.id,
                canonical_key=canonical_key,
                preco_alvo=preco_alvo,
                notificar_queda_preco=notificar,
            )
        except ValueError as erro:
            raise self._traduzir_erro(erro) from erro

        return (
            200,
            {
                "item": self._serializar(item),
            },
        )

    def remover(
        self,
        conta: ContaUsuario,
        canonical_key: str,
    ) -> tuple[int, dict[str, object]]:
        try:
            removido = self._service().remover_watchlist(
                conta_id=conta.id,
                canonical_key=canonical_key,
            )
        except ValueError as erro:
            raise self._traduzir_erro(erro) from erro

        if not removido:
            raise ErroHttpUserFacing(
                404,
                "watchlist_item_nao_encontrado",
                "Item da watchlist nao encontrado.",
            )

        return (
            200,
            {
                "removido": True,
                "canonical_key": canonical_key.strip(),
            },
        )
