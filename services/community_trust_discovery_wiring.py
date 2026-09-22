from __future__ import annotations

from dataclasses import dataclass

from models.community_discovery import (
    DescobertaComunitaria,
)
from models.community_trust import (
    ResultadoRegistroCommunityTrust,
)
from models.community_trust_policy import (
    DecisaoCommunityTrust,
)
from repositories.community_trust_repository import (
    CommunityTrustRepository,
)
from services.community_trust_policy import (
    CommunityTrustPolicyV1,
)


@dataclass(frozen=True, slots=True)
class ResultadoCommunityTrustDiscoveryWiring:
    registro: ResultadoRegistroCommunityTrust
    decisao: DecisaoCommunityTrust
    positivas_na_janela: int


class CommunityTrustDiscoveryWiring:
    TIPO_EVIDENCIA = "community_discovery_terminal"
    ORIGEM = "community_discovery_v1"

    def __init__(
        self,
        repository: CommunityTrustRepository,
    ) -> None:
        self.repository = repository

    def processar(
        self,
        descoberta: DescobertaComunitaria,
    ) -> ResultadoCommunityTrustDiscoveryWiring:
        pre_decisao = CommunityTrustPolicyV1.avaliar(
            descoberta,
            positivas_na_janela=0,
            abuso_confirmado_autoritativamente=False,
        )

        if not pre_decisao.elegivel:
            raise ValueError(
                "Community Trust wiring aceita apenas " "descobertas em estado terminal."
            )

        chave = str(pre_decisao.chave_idempotencia or "").strip()

        if not chave:
            raise RuntimeError("Policy elegivel retornou " "chave de idempotencia vazia.")

        (
            registro,
            decisao,
            positivas_na_janela,
        ) = self.repository.registrar_evidencia_com_decisao_atomica(
            conta_id=descoberta.conta_id,
            chave_idempotencia=chave,
            tipo_evidencia=self.TIPO_EVIDENCIA,
            origem=self.ORIGEM,
            origem_id=descoberta.id,
            ocorrido_em=descoberta.atualizado_em,
            janela_segundos=(CommunityTrustPolicyV1.JANELA_POSITIVA_SEGUNDOS),
            decidir=lambda positivas: (
                CommunityTrustPolicyV1.avaliar(
                    descoberta,
                    positivas_na_janela=positivas,
                    abuso_confirmado_autoritativamente=False,
                )
            ),
        )

        return ResultadoCommunityTrustDiscoveryWiring(
            registro=registro,
            decisao=decisao,
            positivas_na_janela=(positivas_na_janela),
        )
