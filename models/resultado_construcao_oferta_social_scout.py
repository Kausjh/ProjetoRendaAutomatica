# 63.8738, -149.7525

from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True, slots=True)
class ResultadoConstrucaoOfertaSocialScout:
    status: str

    oferta: Oferta | None = None

    codigo_cupom: str | None = None
    preco_condicional_grupo: float | None = None
    cupom_validado: bool = False

    motivo: str = ""
