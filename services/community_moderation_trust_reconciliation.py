from __future__ import annotations

from dataclasses import dataclass

from models.community_moderation import (
    ResultadoRegistroDecisaoCommunityModeration,
)
from repositories.community_moderation_repository import (
    CommunityModerationRepository,
)
from services.community_moderation_authority import (
    CommunityModerationAuthorityV1,
)
from services.community_moderation_trust_bridge import (
    CommunityModerationTrustBridge,
)


@dataclass(frozen=True, slots=True)
class FalhaReconciliacaoModerationTrust:
    moderation_decision_id: str
    denuncia_id: str
    tipo_erro: str
    mensagem: str


@dataclass(frozen=True, slots=True)
class ResultadoReconciliacaoModerationTrust:
    offset_inicial: int
    proximo_offset: int
    examinadas: int
    evidencias_criadas: int
    evidencias_existentes: int
    falhas: tuple[
        FalhaReconciliacaoModerationTrust,
        ...,
    ]


class CommunityModerationTrustReconciliation:
    MAX_LIMITE = 1000

    def __init__(
        self,
        *,
        moderation_repository: CommunityModerationRepository,
        trust_bridge: CommunityModerationTrustBridge,
    ) -> None:
        self.moderation_repository = moderation_repository

        self.trust_bridge = trust_bridge

    @classmethod
    def _normalizar_limite(
        cls,
        limite: int,
    ) -> int:
        if isinstance(
            limite,
            bool,
        ):
            raise ValueError("limite precisa ser inteiro positivo.")

        valor = int(limite)

        if valor < 1:
            raise ValueError("limite precisa ser positivo.")

        return min(
            valor,
            cls.MAX_LIMITE,
        )

    @staticmethod
    def _normalizar_offset(
        offset: int,
    ) -> int:
        if isinstance(
            offset,
            bool,
        ):
            raise ValueError("offset precisa ser inteiro nao negativo.")

        valor = int(offset)

        if valor < 0:
            raise ValueError("offset nao pode ser negativo.")

        return valor

    def reconciliar(
        self,
        *,
        limite: int = 100,
        offset: int = 0,
    ) -> ResultadoReconciliacaoModerationTrust:
        limite_normalizado = self._normalizar_limite(limite)

        offset_normalizado = self._normalizar_offset(offset)

        decisoes = self.moderation_repository.listar_decisoes_abuso_confirmado(
            moderator_actor_id=(CommunityModerationAuthorityV1.ACTOR_ID),
            limite=limite_normalizado,
            offset=offset_normalizado,
        )

        criadas = 0
        existentes = 0

        falhas: list[FalhaReconciliacaoModerationTrust] = []

        for decisao in decisoes:
            denuncia = self.moderation_repository.obter_denuncia(decisao.denuncia_id)

            if denuncia is None:
                falhas.append(
                    FalhaReconciliacaoModerationTrust(
                        moderation_decision_id=(decisao.id),
                        denuncia_id=(decisao.denuncia_id),
                        tipo_erro=("denuncia_nao_encontrada"),
                        mensagem=("Decision persistida sem " "report correspondente."),
                    )
                )

                continue

            if denuncia.estado != "resolved":
                falhas.append(
                    FalhaReconciliacaoModerationTrust(
                        moderation_decision_id=(decisao.id),
                        denuncia_id=(denuncia.id),
                        tipo_erro=("denuncia_nao_resolvida"),
                        mensagem=("confirmed_abuse " "persistido exige report " "resolved."),
                    )
                )

                continue

            resultado_persistido = ResultadoRegistroDecisaoCommunityModeration(
                decisao=decisao,
                denuncia=denuncia,
                criado=False,
            )

            try:
                resultado_bridge = self.trust_bridge.processar_decisao(resultado_persistido)

                if resultado_bridge.criado:
                    criadas += 1

                elif resultado_bridge.status == "idempotent_existing":
                    existentes += 1

                else:
                    falhas.append(
                        FalhaReconciliacaoModerationTrust(
                            moderation_decision_id=(decisao.id),
                            denuncia_id=(denuncia.id),
                            tipo_erro=("status_bridge_inesperado"),
                            mensagem=str(resultado_bridge.status),
                        )
                    )

            except Exception as erro:
                falhas.append(
                    FalhaReconciliacaoModerationTrust(
                        moderation_decision_id=(decisao.id),
                        denuncia_id=(denuncia.id),
                        tipo_erro=(type(erro).__name__),
                        mensagem=str(erro),
                    )
                )

        return ResultadoReconciliacaoModerationTrust(
            offset_inicial=offset_normalizado,
            proximo_offset=(offset_normalizado + len(decisoes)),
            examinadas=len(decisoes),
            evidencias_criadas=criadas,
            evidencias_existentes=existentes,
            falhas=tuple(falhas),
        )
