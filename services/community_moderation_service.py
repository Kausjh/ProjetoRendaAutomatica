from __future__ import annotations

from typing import Protocol

from models.community_moderation import (
    FAMILIA_ABUSO_POR_MOTIVO_DENUNCIA,
    RESULTADOS_MODERACAO_VALIDOS,
    ResultadoRegistroDecisaoCommunityModeration,
)
from repositories.community_moderation_repository import (
    CommunityModerationRepository,
)
from services.community_moderation_authority import (
    CommunityModerationAuthorityV1,
)


class CommunityModerationDecisionBridge(Protocol):
    def processar_decisao(
        self,
        resultado: ResultadoRegistroDecisaoCommunityModeration,
    ) -> object: ...


class PoliticaModeracaoNegada(ValueError):
    pass


class CommunityModerationService:
    def __init__(
        self,
        *,
        repository: CommunityModerationRepository,
        authority: CommunityModerationAuthorityV1,
        trust_bridge: CommunityModerationDecisionBridge | None = None,
    ) -> None:
        self.repository = repository
        self.authority = authority
        self.trust_bridge = trust_bridge

    def registrar_decisao_autorizada(
        self,
        *,
        authorization_header: str | None,
        denuncia_id: str,
        acao_idempotencia: str,
        resultado: str,
        justificativa: str | None,
        ocorrido_em: str,
    ) -> ResultadoRegistroDecisaoCommunityModeration:
        contexto = self.authority.autorizar(authorization_header)

        resultado_normalizado = str(resultado or "").strip()

        if resultado_normalizado not in RESULTADOS_MODERACAO_VALIDOS:
            raise PoliticaModeracaoNegada("Resultado de moderacao invalido.")

        denuncia = self.repository.obter_denuncia(denuncia_id)

        if denuncia is None:
            raise ValueError("Denuncia nao encontrada.")

        familia: str | None = None

        if resultado_normalizado == "confirmed_abuse":
            familia = FAMILIA_ABUSO_POR_MOTIVO_DENUNCIA.get(denuncia.motivo)

            if familia is None:
                raise PoliticaModeracaoNegada(
                    "Motivo da denuncia nao " "autoriza confirmed_abuse " "na policy V1."
                )

        registro = self.repository.registrar_decisao(
            denuncia_id=denuncia.id,
            acao_idempotencia=(acao_idempotencia),
            moderator_actor_id=(contexto.actor_id),
            resultado=resultado_normalizado,
            familia_abuso_confirmado=familia,
            justificativa=justificativa,
            ocorrido_em=ocorrido_em,
        )

        if registro.decisao.resultado == "confirmed_abuse" and self.trust_bridge is not None:
            self.trust_bridge.processar_decisao(registro)

        return registro
