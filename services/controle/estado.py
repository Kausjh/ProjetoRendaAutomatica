from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EstadoProcesso:
    ativo: bool
    pid: int | None


@dataclass(frozen=True, slots=True)
class EstadoFila:
    pendentes: int
    familias: int
    itens_com_familia: int


@dataclass(frozen=True, slots=True)
class EstadoConectividade:
    internet: bool
    telegram: bool
    mercado_livre: bool


@dataclass(frozen=True, slots=True)
class EstadoAdministrativo:
    runtime_ativo: bool
    runtime_pid: int
    encerrando: bool
    pipeline: EstadoProcesso
    publicador: EstadoProcesso
    bot: EstadoProcesso
    fila: EstadoFila
    conectividade: EstadoConectividade
    coletado_em: str

    def como_dict(self) -> dict[str, Any]:
        return asdict(self)
