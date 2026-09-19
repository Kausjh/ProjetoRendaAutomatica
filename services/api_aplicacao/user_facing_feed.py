from __future__ import annotations

from decimal import Decimal

from models.personalized_feed import (
    ItemFeedPersonalizado,
    PaginaFeedPersonalizado,
)
from models.user_identity import ContaUsuario
from services.api_aplicacao.user_facing_http import ErroHttpUserFacing
from services.personalized_feed_service import PersonalizedFeedService


class UserFacingFeedController:
    def __init__(
        self,
        personalized_feed_service: PersonalizedFeedService | None,
    ) -> None:
        self.personalized_feed_service = personalized_feed_service

    def _service(self) -> PersonalizedFeedService:
        service = self.personalized_feed_service
        if service is None:
            raise ErroHttpUserFacing(
                503,
                "feed_personalizado_indisponivel",
                "Feed personalizado indisponivel.",
            )
        return service

    @staticmethod
    def _normalizar_paginacao(
        *,
        limite: object,
        offset: object,
    ) -> tuple[int, int]:
        try:
            limite_int = int(limite)
            offset_int = int(offset)
        except (TypeError, ValueError) as erro:
            raise ErroHttpUserFacing(
                400,
                "paginacao_invalida",
                "limite e offset precisam ser inteiros.",
            ) from erro

        return (
            max(1, min(limite_int, 50)),
            max(0, offset_int),
        )

    @staticmethod
    def _serializar_decimal(
        valor: Decimal | None,
    ) -> str | None:
        if valor is None:
            return None
        return format(valor, ".2f")

    @classmethod
    def _serializar_item(
        cls,
        item: ItemFeedPersonalizado,
    ) -> dict[str, object]:
        return {
            "canonical_key": item.canonical_key,
            "nome_canonico": item.nome_canonico,
            "categoria": item.categoria,
            "marca": item.marca,
            "modelo": item.modelo,
            "score_relevancia": item.score_relevancia,
            "motivos": list(item.motivos),
            "em_watchlist": item.em_watchlist,
            "preco_alvo": cls._serializar_decimal(item.preco_alvo),
            "preco_atual": cls._serializar_decimal(item.preco_atual),
            "marketplace": item.marketplace,
            "identificador": item.identificador,
            "link": item.link,
            "atualizado_em": item.atualizado_em,
        }

    @classmethod
    def _serializar_pagina(
        cls,
        pagina: PaginaFeedPersonalizado,
    ) -> dict[str, object]:
        return {
            "total": pagina.total,
            "limite": pagina.limite,
            "offset": pagina.offset,
            "itens": [cls._serializar_item(item) for item in pagina.itens],
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
            "feed_personalizado_invalido",
            mensagem,
        )

    def listar(
        self,
        conta: ContaUsuario,
        *,
        limite: object = 20,
        offset: object = 0,
    ) -> tuple[int, dict[str, object]]:
        limite_norm, offset_norm = self._normalizar_paginacao(
            limite=limite,
            offset=offset,
        )
        try:
            pagina = self._service().gerar(
                conta_id=conta.id,
                limite=limite_norm,
                offset=offset_norm,
            )
        except ValueError as erro:
            raise self._traduzir_erro_service(erro) from erro
        return 200, self._serializar_pagina(pagina)
