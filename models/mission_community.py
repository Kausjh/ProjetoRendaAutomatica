from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DescobertaAprovadaParaMissao:
    id: str
    conta_id: str
    status: str
    ocorrido_em: str


@dataclass(frozen=True, slots=True)
class ResultadoWiringMissaoCommunity:
    descoberta_id: str
    status: str
    eventos_criados: int
    eventos_idempotentes: int
    eventos_completados: int
    missoes_concluidas_agora: int
    recompensas_criadas: int
    falhas: tuple[str, ...]

    @property
    def sucesso(self) -> bool:
        return self.status == "success" and not self.falhas


@dataclass(frozen=True, slots=True)
class ResultadoReconciliacaoMissoes:
    descobertas_processadas: int
    eventos_criados: int
    eventos_idempotentes: int
    eventos_completados: int
    missoes_concluidas_agora: int
    recompensas_criadas: int
    falhas: tuple[str, ...]

    @property
    def sucesso(self) -> bool:
        return not self.falhas
