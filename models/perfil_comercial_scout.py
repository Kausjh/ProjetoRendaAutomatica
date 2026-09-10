# 63.8738, -149.7525

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PerfilComercialScout:
    """
    Visao comercial derivada de um SinalScout.

    Este modelo nao representa preco oficial, preco promocional
    confirmado nem historico de preco.

    Ele existe exclusivamente para organizar sinais de discovery.
    """

    fonte: str
    id_externo: str
    tipo_sinal: str
    titulo: str

    marketplace: str | None = None
    tipo_destino: str | None = None

    parceiro_id: str | None = None
    parceiro_nome: str | None = None

    codigo_voucher: str | None = None

    inicio: str | None = None
    fim: str | None = None

    regioes: tuple[str, ...] = ()

    estrategia_discovery: str | None = None
    termos_descoberta: tuple[str, ...] = ()

    dimensoes: tuple[str, ...] = ()
    evidencias: tuple[str, ...] = ()

    landing_page: bool = False
    utilizavel_discovery: bool = False
