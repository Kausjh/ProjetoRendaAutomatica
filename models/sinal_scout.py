# 63.8738, -149.7525

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SinalScout:
    fonte: str
    id_externo: str
    tipo: str
    titulo: str
    url: str

    advertiser_id: str | None = None
    advertiser_nome: str | None = None

    descricao: str = ""
    termos: str = ""

    url_tracking: str | None = None
    codigo_voucher: str | None = None

    inicio: str | None = None
    fim: str | None = None

    regioes: tuple[str, ...] = ()
