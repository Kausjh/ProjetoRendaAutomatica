from __future__ import annotations

from dataclasses import dataclass

from models.community_moderation import (
    FAMILIA_ABUSO_POR_MOTIVO_DENUNCIA,
    FAMILIAS_ABUSO_CONFIRMADO,
    ORIGEM_TRUST_MODERACAO,
    TIPO_EVIDENCIA_TRUST_MODERACAO,
    ResultadoRegistroDecisaoCommunityModeration,
)
from models.community_trust import (
    EvidenciaCommunityTrust,
    PerfilCommunityTrust,
)
from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
    ConflitoIdempotenciaCommunityTrust,
)
from services.community_moderation_authority import (
    CommunityModerationAuthorityV1,
)


class DecisaoModeracaoNaoAutoritativa(ValueError):
    pass


class ConflitoModerationTrustBridge(ValueError):
    pass


class TargetModerationTrustBridgeNaoEncontrado(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoCommunityModerationTrustBridge:
    status: str
    discovery_id: str
    conta_id: str | None
    moderation_decision_id: str
    evidencia: EvidenciaCommunityTrust | None
    perfil: PerfilCommunityTrust | None
    criado: bool


class CommunityModerationTrustBridge:
    POLICY_VERSION = "community-moderation-trust-bridge-v1"

    IDEMPOTENCY_PREFIX = "v1:community-moderation:" "community-discovery"

    DEDUPLICATION_SCOPE = "one_negative_per_discovery"

    def __init__(
        self,
        *,
        discovery_repository: CommunityDiscoveryRepository,
        trust_repository: CommunityTrustRepository,
    ) -> None:
        self.discovery_repository = discovery_repository
        self.trust_repository = trust_repository

    @classmethod
    def chave_para_discovery(
        cls,
        discovery_id: str,
    ) -> str:
        identificador = str(discovery_id or "").strip()

        if not identificador:
            raise ValueError("discovery_id e obrigatorio.")

        return f"{cls.IDEMPOTENCY_PREFIX}:" f"{identificador}:" "confirmed-abuse"

    @classmethod
    def _validar_evidencia_existente(
        cls,
        evidencia: EvidenciaCommunityTrust,
        *,
        conta_id: str,
        discovery_id: str,
        chave_idempotencia: str,
    ) -> None:
        if evidencia.conta_id != conta_id:
            raise (ConflitoModerationTrustBridge("Evidencia existente pertence " "a outra conta."))

        if evidencia.chave_idempotencia != chave_idempotencia:
            raise (ConflitoModerationTrustBridge("Chave persistida diverge " "da chave canonica."))

        if evidencia.tipo_evidencia != TIPO_EVIDENCIA_TRUST_MODERACAO:
            raise (
                ConflitoModerationTrustBridge(
                    "Chave canonica ocupada por " "tipo de evidencia diferente."
                )
            )

        if evidencia.classificacao != "negative":
            raise (ConflitoModerationTrustBridge("Evidencia canonica nao e negative."))

        if evidencia.origem != ORIGEM_TRUST_MODERACAO:
            raise (ConflitoModerationTrustBridge("Origem da evidencia canonica " "e invalida."))

        if evidencia.politica_versao != cls.POLICY_VERSION:
            raise (
                ConflitoModerationTrustBridge("Policy version da evidencia " "canonica divergiu.")
            )

        if evidencia.motivo not in FAMILIAS_ABUSO_CONFIRMADO:
            raise (
                ConflitoModerationTrustBridge(
                    "Motivo da evidencia canonica " "nao e abuso confirmado."
                )
            )

        metadados = evidencia.metadados

        if metadados.get("target_type") != "community_discovery":
            raise (ConflitoModerationTrustBridge("Target type da evidencia " "canonica divergiu."))

        if metadados.get("target_id") != discovery_id:
            raise (ConflitoModerationTrustBridge("Target id da evidencia " "canonica divergiu."))

        if metadados.get("deduplication_scope") != cls.DEDUPLICATION_SCOPE:
            raise (
                ConflitoModerationTrustBridge("Escopo de deduplicacao " "da evidencia divergiu.")
            )

        if metadados.get("impacto_unidades") != -1:
            raise (ConflitoModerationTrustBridge("Impacto da evidencia " "canonica divergiu."))

        if metadados.get("moderation_decision_id") != evidencia.origem_id:
            raise (
                ConflitoModerationTrustBridge("Origin id nao corresponde " "a decision de origem.")
            )

    def _resultado_existente(
        self,
        *,
        evidencia: EvidenciaCommunityTrust,
        conta_id: str,
        discovery_id: str,
        moderation_decision_id: str,
        chave_idempotencia: str,
    ) -> ResultadoCommunityModerationTrustBridge:
        self._validar_evidencia_existente(
            evidencia,
            conta_id=conta_id,
            discovery_id=discovery_id,
            chave_idempotencia=(chave_idempotencia),
        )

        perfil = self.trust_repository.obter_perfil(conta_id)

        return ResultadoCommunityModerationTrustBridge(
            status="idempotent_existing",
            discovery_id=discovery_id,
            conta_id=conta_id,
            moderation_decision_id=(moderation_decision_id),
            evidencia=evidencia,
            perfil=perfil,
            criado=False,
        )

    def processar_decisao(
        self,
        resultado: ResultadoRegistroDecisaoCommunityModeration,
    ) -> ResultadoCommunityModerationTrustBridge:
        decisao = resultado.decisao
        denuncia = resultado.denuncia

        if decisao.denuncia_id != denuncia.id:
            raise (ConflitoModerationTrustBridge("Decision e report nao " "correspondem."))

        if decisao.resultado != "confirmed_abuse":
            return ResultadoCommunityModerationTrustBridge(
                status="ignored_non_confirmed",
                discovery_id=(denuncia.target_id),
                conta_id=None,
                moderation_decision_id=(decisao.id),
                evidencia=None,
                perfil=None,
                criado=False,
            )

        if decisao.moderator_actor_id != CommunityModerationAuthorityV1.ACTOR_ID:
            raise (
                DecisaoModeracaoNaoAutoritativa(
                    "Decision confirmed_abuse " "nao pertence ao principal " "autoritativo."
                )
            )

        familia_esperada = FAMILIA_ABUSO_POR_MOTIVO_DENUNCIA.get(denuncia.motivo)

        if familia_esperada is None:
            raise (
                DecisaoModeracaoNaoAutoritativa(
                    "Motivo do report nao " "autoriza evidencia negative."
                )
            )

        if decisao.familia_abuso_confirmado != familia_esperada:
            raise (
                DecisaoModeracaoNaoAutoritativa(
                    "Familia de abuso da decision " "diverge da policy server-side."
                )
            )

        if denuncia.target_type != "community_discovery":
            raise (
                DecisaoModeracaoNaoAutoritativa(
                    "Target type nao suportado " "pela Trust Bridge V1."
                )
            )

        discovery = self.discovery_repository.obter_por_id(denuncia.target_id)

        if discovery is None:
            raise (
                TargetModerationTrustBridgeNaoEncontrado(
                    "Community discovery alvo " "nao encontrada."
                )
            )

        conta_id = str(discovery.conta_id or "").strip()

        if not conta_id:
            raise (ConflitoModerationTrustBridge("Community discovery sem " "conta contribuidora."))

        discovery_id = str(discovery.id)

        chave = self.chave_para_discovery(discovery_id)

        existente = self.trust_repository.obter_evidencia_por_chave(
            conta_id=conta_id,
            chave_idempotencia=chave,
        )

        if existente is not None:
            return self._resultado_existente(
                evidencia=existente,
                conta_id=conta_id,
                discovery_id=discovery_id,
                moderation_decision_id=(decisao.id),
                chave_idempotencia=chave,
            )

        metadados = {
            "moderation_decision_id": (decisao.id),
            "moderation_report_id": (denuncia.id),
            "moderator_actor_id": (decisao.moderator_actor_id),
            "report_reason": (denuncia.motivo),
            "confirmed_abuse_family": (familia_esperada),
            "target_type": ("community_discovery"),
            "target_id": discovery_id,
            "impacted_account_source": ("community_discovery.conta_id"),
            "deduplication_scope": (self.DEDUPLICATION_SCOPE),
            "impacto_unidades": -1,
            "bridge_policy_version": (self.POLICY_VERSION),
        }

        try:
            registro = self.trust_repository.registrar_evidencia(
                conta_id=conta_id,
                chave_idempotencia=chave,
                tipo_evidencia=(TIPO_EVIDENCIA_TRUST_MODERACAO),
                classificacao="negative",
                origem=(ORIGEM_TRUST_MODERACAO),
                origem_id=decisao.id,
                motivo=familia_esperada,
                politica_versao=(self.POLICY_VERSION),
                metadados=metadados,
                ocorrido_em=(decisao.ocorrido_em),
            )

        except ConflitoIdempotenciaCommunityTrust:
            # Outra decision para a mesma discovery
            # pode ter vencido a corrida entre o
            # pre-check e o BEGIN IMMEDIATE do ledger.
            existente_pos_conflito = self.trust_repository.obter_evidencia_por_chave(
                conta_id=conta_id,
                chave_idempotencia=chave,
            )

            if existente_pos_conflito is None:
                raise

            return self._resultado_existente(
                evidencia=(existente_pos_conflito),
                conta_id=conta_id,
                discovery_id=discovery_id,
                moderation_decision_id=(decisao.id),
                chave_idempotencia=chave,
            )

        status = "created" if registro.criado else "idempotent_existing"

        return ResultadoCommunityModerationTrustBridge(
            status=status,
            discovery_id=discovery_id,
            conta_id=conta_id,
            moderation_decision_id=(decisao.id),
            evidencia=registro.evidencia,
            perfil=registro.perfil,
            criado=registro.criado,
        )
