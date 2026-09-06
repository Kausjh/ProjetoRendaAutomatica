# 63.8738, -149.7525

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResultadoDeteccaoSocialScout:
    classificacao: str
    utilizavel: bool

    titulo: str = ""
    marketplace: str | None = None

    preco_original: float | None = None
    preco_oferta: float | None = None
    preco_final: float | None = None

    desconto_anunciado_percentual: float | None = None
    desconto_cupom_percentual: float | None = None

    codigo_cupom: str | None = None
    cupons: tuple[str, ...] = ()

    links: tuple[str, ...] = ()

    motivo: str = ""
