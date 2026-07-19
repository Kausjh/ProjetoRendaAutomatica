from dataclasses import dataclass


@dataclass
class ResultadoFiltro:
    aprovada: bool
    motivo: str