from __future__ import annotations

from dataclasses import dataclass

TARGET_TYPES_VALIDOS = frozenset(
    {
        "community_discovery",
    }
)


MOTIVOS_DENUNCIA_VALIDOS = frozenset(
    {
        "spam",
        "fraud",
        "malicious_link",
        "abuse",
        "off_topic",
        "duplicate",
        "other",
    }
)


ESTADOS_DENUNCIA_VALIDOS = frozenset(
    {
        "received",
        "under_review",
        "resolved",
    }
)


RESULTADOS_MODERACAO_VALIDOS = frozenset(
    {
        "confirmed_abuse",
        "dismissed",
        "keep_under_review",
    }
)


FAMILIAS_ABUSO_CONFIRMADO = frozenset(
    {
        "abuso_confirmado",
        "spam_confirmado",
        "fraude_confirmada",
        "link_malicioso_confirmado",
    }
)


FAMILIA_ABUSO_POR_MOTIVO_DENUNCIA = {
    "spam": "spam_confirmado",
    "fraud": "fraude_confirmada",
    "malicious_link": "link_malicioso_confirmado",
    "abuse": "abuso_confirmado",
}


TIPO_EVIDENCIA_TRUST_MODERACAO = "community_moderation_confirmed_abuse"


ORIGEM_TRUST_MODERACAO = "community_moderation_v1"


POLITICA_MODERACAO_VERSAO = "community-moderation-foundation-v1"


@dataclass(frozen=True, slots=True)
class DenunciaCommunityModeration:
    id: str
    reporter_conta_id: str
    target_type: str
    target_id: str
    motivo: str
    detalhes: str | None
    estado: str
    criado_em: str
    atualizado_em: str


@dataclass(frozen=True, slots=True)
class DecisaoCommunityModeration:
    id: str
    denuncia_id: str
    moderator_actor_id: str
    resultado: str
    familia_abuso_confirmado: str | None
    justificativa: str | None
    ocorrido_em: str


@dataclass(frozen=True, slots=True)
class ResultadoRegistroDenunciaCommunityModeration:
    denuncia: DenunciaCommunityModeration
    criado: bool


@dataclass(frozen=True, slots=True)
class ResultadoRegistroDecisaoCommunityModeration:
    decisao: DecisaoCommunityModeration
    denuncia: DenunciaCommunityModeration
    criado: bool
