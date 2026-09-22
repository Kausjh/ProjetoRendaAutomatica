from __future__ import annotations

from dataclasses import dataclass

from repositories.community_trust_reconciliation_repository import (
    CommunityTrustReconciliationRepository,
)
from services.community_trust_terminal_hook import (
    CommunityTrustTerminalHook,
)


@dataclass(frozen=True, slots=True)
class ResultadoCommunityTrustReconciliation:
    candidatos: int
    processados: int
    criados: int
    idempotentes: int
    falhas: int
    falhas_detalhes: tuple[str, ...]


class CommunityTrustReconciliationService:
    def __init__(
        self,
        *,
        repository: CommunityTrustReconciliationRepository,
        terminal_hook: CommunityTrustTerminalHook,
    ) -> None:
        self.repository = repository
        self.terminal_hook = terminal_hook

    def reconciliar_lote(
        self,
        *,
        limite: int = 500,
    ) -> ResultadoCommunityTrustReconciliation:
        candidatos = self.repository.listar_terminais_sem_evidencia(
            limite=limite,
        )

        processados = 0
        criados = 0
        idempotentes = 0
        falhas_detalhes: list[str] = []

        for descoberta in candidatos:
            try:
                resultado = self.terminal_hook.processar_terminal(
                    descoberta_id=(descoberta.id),
                    conta_id=(descoberta.conta_id),
                    status=(descoberta.status),
                    ocorrido_em=(descoberta.atualizado_em),
                )
            except Exception as erro:
                falhas_detalhes.append(
                    (f"{descoberta.id}:" f"{type(erro).__name__}:" f"{erro}")[:700]
                )
                continue

            if not resultado.sucesso:
                motivo = ";".join(resultado.falhas)

                falhas_detalhes.append((f"{descoberta.id}:" f"{motivo}")[:700])
                continue

            processados += 1

            if resultado.criado is True:
                criados += 1
            else:
                idempotentes += 1

        return ResultadoCommunityTrustReconciliation(
            candidatos=len(candidatos),
            processados=processados,
            criados=criados,
            idempotentes=idempotentes,
            falhas=len(falhas_detalhes),
            falhas_detalhes=tuple(falhas_detalhes),
        )
