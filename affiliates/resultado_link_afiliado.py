from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoLinkAfiliado:
    link_original: str
    link_publicacao: str
    afiliador_utilizado: str
    foi_transformado: bool
