from __future__ import annotations

from dataclasses import dataclass

from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from services.community_trust_discovery_wiring import (
    CommunityTrustDiscoveryWiring,
)


@dataclass(frozen=True, slots=True)
class ResultadoCommunityTrustTerminalHook:
    sucesso: bool
    falhas: tuple[str, ...]
    evidencia_id: str | None = None
    criado: bool | None = None
    classificacao: str | None = None


class CommunityTrustTerminalHook:
    STATUS_TERMINAIS = frozenset(
        {
            "approved",
            "rejected",
        }
    )

    def __init__(
        self,
        discovery_repository: CommunityDiscoveryRepository,
        trust_wiring: CommunityTrustDiscoveryWiring,
    ) -> None:
        self.discovery_repository = discovery_repository
        self.trust_wiring = trust_wiring

    @staticmethod
    def _falha(
        motivo: str,
    ) -> ResultadoCommunityTrustTerminalHook:
        return ResultadoCommunityTrustTerminalHook(
            sucesso=False,
            falhas=(motivo,),
        )

    def processar_terminal(
        self,
        *,
        descoberta_id: str,
        conta_id: str,
        status: str,
        ocorrido_em: str,
    ) -> ResultadoCommunityTrustTerminalHook:
        discovery_id = str(descoberta_id or "").strip()

        account_id = str(conta_id or "").strip()

        terminal_status = str(status or "").strip()

        occurred_at = str(ocorrido_em or "").strip()

        if not discovery_id:
            return self._falha("descoberta_id_ausente")

        if not account_id:
            return self._falha("conta_id_ausente")

        if terminal_status not in self.STATUS_TERMINAIS:
            return self._falha("status_nao_terminal")

        if not occurred_at:
            return self._falha("ocorrido_em_ausente")

        descoberta = self.discovery_repository.obter_por_id(discovery_id)

        if descoberta is None:
            return self._falha("descoberta_nao_encontrada")

        if descoberta.conta_id != account_id:
            return self._falha("conta_id_divergente")

        if descoberta.status != terminal_status:
            return self._falha("status_divergente")

        if descoberta.status not in self.STATUS_TERMINAIS:
            return self._falha("fonte_nao_terminal")

        if descoberta.atualizado_em != occurred_at:
            return self._falha("ocorrido_em_divergente")

        try:
            resultado = self.trust_wiring.processar(descoberta)
        except Exception as erro:
            mensagem = f"{type(erro).__name__}:" f"{erro}"

            return self._falha(mensagem[:500])

        return ResultadoCommunityTrustTerminalHook(
            sucesso=True,
            falhas=(),
            evidencia_id=(resultado.registro.evidencia.id),
            criado=resultado.registro.criado,
            classificacao=(resultado.registro.evidencia.classificacao),
        )
