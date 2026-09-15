from __future__ import annotations

from dataclasses import dataclass

TIPO_MUDANCA_PRECO = "mudanca_preco"
TIPO_NOVO_MENOR_PRECO_HISTORICO = "novo_menor_preco_historico"


@dataclass(frozen=True, slots=True)
class EventoAlertEngine:
    fingerprint: str
    tipo: str
    chave_canonica: str
    nome_canonico: str
    marketplace: str
    identificador: str
    preco_atual: float
    preco_anterior: float | None
    criado_em: str


@dataclass(frozen=True, slots=True)
class ResultadoAlertEngine:
    status: str
    processado: bool
    baseline_inicializada: bool
    alertas_gerados: int
    tipos_gerados: tuple[str, ...]
    chave_canonica: str | None
    marketplace: str | None
    identificador: str | None
    motivo: str
    eventos: tuple[EventoAlertEngine, ...] = ()
