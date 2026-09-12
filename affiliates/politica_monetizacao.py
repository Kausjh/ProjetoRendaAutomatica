from __future__ import annotations

from urllib.parse import urlparse


class PoliticaMonetizacao:
    """Centraliza quando uma URL precisa de monetizacao confirmada."""

    DOMINIOS_MARKETPLACE_MONETIZAVEL = (
        "mercadolivre.com.br",
        "shopee.com.br",
        "aliexpress.com",
        "kabum.com.br",
        "amazon.com.br",
    )

    # Estes dominios podem representar links comerciais/encurtados,
    # mas o dominio sozinho nunca prova que pertencem a nossa afiliacao.
    # Se chegarem diretamente ao publicador sem transformacao interna
    # confirmada, o comportamento correto e fail-closed.
    DOMINIOS_INTERMEDIARIOS_COMERCIAIS = (
        "meli.la",
        "amzn.to",
        "link.amazon",
        "tidd.ly",
        "awin1.com",
    )

    @staticmethod
    def _obter_host(link: str) -> str:
        if not isinstance(link, str):
            return ""

        host = (urlparse(link.strip()).hostname or "").lower()

        if host.startswith("www."):
            host = host[4:]

        return host

    @staticmethod
    def _host_corresponde(host: str, dominio_base: str) -> bool:
        return host == dominio_base or host.endswith(f".{dominio_base}")

    @classmethod
    def exige_confirmacao_afiliacao(cls, link: str) -> bool:
        host = cls._obter_host(link)

        if not host:
            return False

        dominios = cls.DOMINIOS_MARKETPLACE_MONETIZAVEL + cls.DOMINIOS_INTERMEDIARIOS_COMERCIAIS

        return any(cls._host_corresponde(host, dominio_base) for dominio_base in dominios)

    @classmethod
    def exige_preparo_chrome_mercado_livre(cls, link: str) -> bool:
        host = cls._obter_host(link)

        if not host:
            return False

        return cls._host_corresponde(
            host,
            "mercadolivre.com.br",
        )
