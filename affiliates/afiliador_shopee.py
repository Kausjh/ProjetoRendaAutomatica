import logging
from urllib.parse import urlparse

from affiliates.base_afiliador import BaseAfiliador
from services.shopee_api_service import ShopeeApiService

logger = logging.getLogger(__name__)

# 63.8738, -149.7525


class AfiliadorShopee(BaseAfiliador):
    def __init__(
        self,
        nome: str,
        dominios: list[str],
        service: ShopeeApiService | None = None,
    ) -> None:
        nome_normalizado = nome.strip()

        if not nome_normalizado:
            raise ValueError("O nome do afiliador da Shopee n?o pode ficar vazio.")

        dominios_normalizados = [dominio.strip().lower() for dominio in dominios if dominio.strip()]

        if not dominios_normalizados:
            raise ValueError("O afiliador da Shopee precisa possuir " "pelo menos um dom?nio.")

        self._nome = nome_normalizado
        self.dominios = dominios_normalizados
        self.service = service or ShopeeApiService()

    @property
    def nome(self) -> str:
        return self._nome

    def suporta(self, link: str) -> bool:
        dominio_link = (urlparse(link).hostname or "").lower()

        if dominio_link.startswith("www."):
            dominio_link = dominio_link[4:]

        for dominio in self.dominios:
            dominio_normalizado = dominio

            if dominio_normalizado.startswith("www."):
                dominio_normalizado = dominio_normalizado[4:]

            if dominio_link == dominio_normalizado or dominio_link.endswith(
                f".{dominio_normalizado}"
            ):
                return True

        return False

    def gerar_link(self, link_original: str) -> str:
        link_afiliado = self.service.gerar_shortlink(link_original)

        logger.info(
            "Link afiliado da Shopee pronto: %s",
            link_afiliado,
        )

        return link_afiliado
