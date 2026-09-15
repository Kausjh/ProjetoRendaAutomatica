from __future__ import annotations

from models.community_discovery import DescobertaComunitaria
from models.user_identity import ContaUsuario
from services.api_aplicacao.user_facing_http import ErroHttpUserFacing
from services.community_discovery_service import (
    CommunityDiscoveryService,
    LimiteDescobertasComunitariasExcedido,
)


class UserFacingCommunityDiscoveryController:
    def __init__(
        self,
        service: CommunityDiscoveryService | None,
    ) -> None:
        self.service = service

    def _service(self) -> CommunityDiscoveryService:
        if self.service is None:
            raise ErroHttpUserFacing(
                503,
                "descoberta_comunitaria_indisponivel",
                "Descoberta comunitaria indisponivel.",
            )
        return self.service

    @staticmethod
    def _serializar(item: DescobertaComunitaria) -> dict[str, object]:
        return {
            "id": item.id,
            "url": item.url,
            "marketplace": item.marketplace,
            "status": item.status,
            "motivo_status": item.motivo_status,
            "canonical_key": item.canonical_key,
            "criado_em": item.criado_em,
            "atualizado_em": item.atualizado_em,
        }

    def listar(
        self,
        conta: ContaUsuario,
    ) -> tuple[int, dict[str, object]]:
        if not conta.ativa:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            )

        itens = self._service().listar(
            conta_id=conta.id,
            limite=50,
        )

        return (
            200,
            {
                "total": len(itens),
                "itens": [self._serializar(item) for item in itens],
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

        desconhecidos = set(payload) - {"url"}
        if desconhecidos:
            raise ErroHttpUserFacing(
                400,
                "payload_descoberta_invalido",
                "O envio aceita somente o campo url.",
            )

        url = payload.get("url")
        if not isinstance(url, str):
            raise ErroHttpUserFacing(
                400,
                "payload_descoberta_invalido",
                "Informe o campo url como texto.",
            )

        try:
            item, criada = self._service().registrar(
                conta_id=conta.id,
                url=url,
            )
        except LimiteDescobertasComunitariasExcedido as erro:
            raise ErroHttpUserFacing(
                429,
                "limite_descobertas_excedido",
                str(erro),
            ) from erro
        except ValueError as erro:
            raise ErroHttpUserFacing(
                400,
                "descoberta_invalida",
                str(erro),
            ) from erro

        return (
            201 if criada else 200,
            {
                "item": self._serializar(item),
                "duplicada": not criada,
            },
        )
