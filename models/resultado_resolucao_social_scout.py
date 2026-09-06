# 63.8738, -149.7525

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResultadoResolucaoSocialScout:
    fonte: str
    id_externo: str

    status: str

    marketplace: str | None = None
    tipo_destino: str | None = None

    url_original: str | None = None
    url_destino: str | None = None

    id_produto: str | None = None
    id_anuncio: str | None = None

    http_status: int | None = None

    motivo: str = ""
