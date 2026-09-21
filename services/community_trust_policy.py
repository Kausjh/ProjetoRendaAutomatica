from __future__ import annotations

from models.community_discovery import (
    DescobertaComunitaria,
)
from models.community_trust_policy import (
    DecisaoCommunityTrust,
)


class CommunityTrustPolicyV1:
    POLITICA_VERSAO = "community-trust-production-v1"

    JANELA_POSITIVA_SEGUNDOS = 86400
    LIMITE_POSITIVO_POR_JANELA = 10

    IMPACTO_POSITIVO = 1
    IMPACTO_NEUTRO = 0
    IMPACTO_NEGATIVO = -1

    STATUS_TERMINAIS = frozenset(
        {
            "approved",
            "rejected",
        }
    )

    STATUS_NAO_TERMINAIS = frozenset(
        {
            "received",
            "processing",
            "retry",
        }
    )

    APROVACOES_POSITIVAS = ("pipeline_processada",)

    APROVACOES_DUPLICADAS_NEUTRAS = ("coletor_duplicada",)

    ABUSOS_CONFIRMADOS = (
        "abuso_confirmado",
        "spam_confirmado",
        "fraude_confirmada",
        "link_malicioso_confirmado",
    )

    MOTIVOS_TECNICOS_PREFIXOS = (
        "limite_tentativas:",
        "erro_resolucao_",
        "erro_validacao_",
        "erro_api_catalogo_mercado_livre:",
        "erro_avaliacao_mercado_livre:",
        "community_discovery_adapter_exception:",
        "processing_timeout",
        "timeout_",
        "falha_api_",
    )

    MOTIVOS_CAPACIDADE = (
        "amazon_sem_processador_de_produto",
        "marketplace_comunitario_nao_suportado",
        "mercado_livre_sem_product_id_catalogo",
        ("titulo_oficial_ausente_para_" "community_discovery_link_only"),
    )

    MOTIVOS_ESTADO_PREFIXOS = (
        ("mercado_livre_sem_publicacao_" "catalogo_com_preco_valido"),
        "produto_",
        "validacao_",
        "preco_oficial_",
        "falha_construcao_oferta_comunitaria",
        "coletor_fora_nicho",
        "produto_invalido",
    )

    @staticmethod
    def _normalizar(
        valor: object | None,
    ) -> str:
        return str(valor or "").strip().casefold()

    @classmethod
    def _familia(
        cls,
        motivo: str,
        familias: tuple[str, ...],
    ) -> bool:
        for familia in familias:
            normalizada = cls._normalizar(familia)

            if motivo == normalizada:
                return True

            if motivo.startswith(normalizada + ":"):
                return True

        return False

    @staticmethod
    def _prefixo(
        motivo: str,
        prefixos: tuple[str, ...],
    ) -> bool:
        return any(motivo.startswith(prefixo.casefold()) for prefixo in prefixos)

    @classmethod
    def _chave(
        cls,
        descoberta_id: str,
    ) -> str:
        identificador = str(descoberta_id or "").strip()

        if not identificador:
            raise ValueError("descoberta_id nao pode ser vazio.")

        return "v1:community-discovery:" + identificador

    @classmethod
    def _resultado(
        cls,
        *,
        descoberta: DescobertaComunitaria,
        elegivel: bool,
        classificacao: str | None,
        impacto: int,
        motivo_politica: str,
        positivas_na_janela: int,
        abuso_confirmado_autoritativamente: bool = False,
    ) -> DecisaoCommunityTrust:
        chave = None

        if elegivel:
            chave = cls._chave(descoberta.id)

        return DecisaoCommunityTrust(
            elegivel=elegivel,
            classificacao=classificacao,
            impacto_unidades=int(impacto),
            politica_versao=(cls.POLITICA_VERSAO),
            chave_idempotencia=chave,
            motivo_politica=(motivo_politica),
            metadados={
                "source_domain": ("community_discovery"),
                "source_id": descoberta.id,
                "source_status": (descoberta.status),
                "source_reason": (descoberta.motivo_status),
                "canonical_key": (descoberta.canonical_key),
                "tentativas": int(descoberta.tentativas),
                "positive_window_seconds": (cls.JANELA_POSITIVA_SEGUNDOS),
                "positive_window_limit": (cls.LIMITE_POSITIVO_POR_JANELA),
                "positive_count_before": (positivas_na_janela),
                "positive_window_atomic_enforcement_required": True,
                "confirmed_abuse_authority": (abuso_confirmado_autoritativamente),
            },
        )

    @classmethod
    def avaliar(
        cls,
        descoberta: DescobertaComunitaria,
        *,
        positivas_na_janela: int = 0,
        abuso_confirmado_autoritativamente: bool = False,
    ) -> DecisaoCommunityTrust:
        if isinstance(
            positivas_na_janela,
            bool,
        ) or not isinstance(
            positivas_na_janela,
            int,
        ):
            raise ValueError("positivas_na_janela invalido: precisa ser int.")

        if not isinstance(
            abuso_confirmado_autoritativamente,
            bool,
        ):
            raise ValueError("abuso_confirmado_autoritativamente " "precisa ser bool.")

        positivas = positivas_na_janela

        if positivas < 0:
            raise ValueError("positivas_na_janela " "nao pode ser negativo.")

        status = cls._normalizar(descoberta.status)

        motivo = cls._normalizar(descoberta.motivo_status)

        if status in cls.STATUS_NAO_TERMINAIS:
            return cls._resultado(
                descoberta=descoberta,
                elegivel=False,
                classificacao=None,
                impacto=cls.IMPACTO_NEUTRO,
                motivo_politica=("status_nao_terminal"),
                positivas_na_janela=(positivas),
            )

        if status not in cls.STATUS_TERMINAIS:
            return cls._resultado(
                descoberta=descoberta,
                elegivel=False,
                classificacao=None,
                impacto=cls.IMPACTO_NEUTRO,
                motivo_politica=("status_desconhecido"),
                positivas_na_janela=(positivas),
            )

        if status == "approved":
            if cls._familia(
                motivo,
                cls.APROVACOES_DUPLICADAS_NEUTRAS,
            ):
                return cls._resultado(
                    descoberta=descoberta,
                    elegivel=True,
                    classificacao="neutral",
                    impacto=cls.IMPACTO_NEUTRO,
                    motivo_politica=("approved_duplicate_downstream"),
                    positivas_na_janela=(positivas),
                )

            if cls._familia(
                motivo,
                cls.APROVACOES_POSITIVAS,
            ):
                if positivas >= cls.LIMITE_POSITIVO_POR_JANELA:
                    return cls._resultado(
                        descoberta=descoberta,
                        elegivel=True,
                        classificacao="neutral",
                        impacto=cls.IMPACTO_NEUTRO,
                        motivo_politica=("positive_window_cap_exceeded"),
                        positivas_na_janela=(positivas),
                    )

                return cls._resultado(
                    descoberta=descoberta,
                    elegivel=True,
                    classificacao="positive",
                    impacto=cls.IMPACTO_POSITIVO,
                    motivo_politica=("approved_pipeline_processed"),
                    positivas_na_janela=(positivas),
                )

            return cls._resultado(
                descoberta=descoberta,
                elegivel=True,
                classificacao="neutral",
                impacto=cls.IMPACTO_NEUTRO,
                motivo_politica=("approved_reason_not_positive"),
                positivas_na_janela=(positivas),
            )

        if cls._familia(
            motivo,
            cls.ABUSOS_CONFIRMADOS,
        ):
            if not abuso_confirmado_autoritativamente:
                return cls._resultado(
                    descoberta=descoberta,
                    elegivel=True,
                    classificacao="neutral",
                    impacto=cls.IMPACTO_NEUTRO,
                    motivo_politica=("confirmed_abuse_missing_authority"),
                    positivas_na_janela=(positivas),
                )

            return cls._resultado(
                descoberta=descoberta,
                elegivel=True,
                classificacao="negative",
                impacto=cls.IMPACTO_NEGATIVO,
                motivo_politica=("confirmed_abuse"),
                positivas_na_janela=(positivas),
                abuso_confirmado_autoritativamente=True,
            )

        if cls._prefixo(
            motivo,
            cls.MOTIVOS_TECNICOS_PREFIXOS,
        ):
            return cls._resultado(
                descoberta=descoberta,
                elegivel=True,
                classificacao="neutral",
                impacto=cls.IMPACTO_NEUTRO,
                motivo_politica=("technical_or_system_rejection"),
                positivas_na_janela=(positivas),
            )

        if cls._familia(
            motivo,
            cls.MOTIVOS_CAPACIDADE,
        ):
            return cls._resultado(
                descoberta=descoberta,
                elegivel=True,
                classificacao="neutral",
                impacto=cls.IMPACTO_NEUTRO,
                motivo_politica=("unsupported_capability_rejection"),
                positivas_na_janela=(positivas),
            )

        if cls._prefixo(
            motivo,
            cls.MOTIVOS_ESTADO_PREFIXOS,
        ):
            return cls._resultado(
                descoberta=descoberta,
                elegivel=True,
                classificacao="neutral",
                impacto=cls.IMPACTO_NEUTRO,
                motivo_politica=("market_or_quality_rejection"),
                positivas_na_janela=(positivas),
            )

        return cls._resultado(
            descoberta=descoberta,
            elegivel=True,
            classificacao="neutral",
            impacto=cls.IMPACTO_NEUTRO,
            motivo_politica=("rejection_reason_unclassified"),
            positivas_na_janela=(positivas),
        )
