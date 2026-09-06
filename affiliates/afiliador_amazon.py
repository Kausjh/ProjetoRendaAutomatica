from __future__ import annotations

import logging
from urllib.parse import urlparse

from affiliates.base_afiliador import BaseAfiliador
from repositories.links_afiliados_amazon_repository import (
    LinksAfiliadosAmazonRepository,
)

# 63.8738, -149.7525

logger = logging.getLogger(__name__)


class AfiliadorAmazon(BaseAfiliador):
    """Usa exclusivamente links Amazon previamente gerados pelo SiteStripe."""

    def __init__(
        self,
        nome: str,
        dominios: list[str],
        repository: LinksAfiliadosAmazonRepository | None = None,
    ) -> None:
        self._nome = nome.strip()

        if not self._nome:
            raise ValueError("O nome do afiliador Amazon " "nao pode ficar vazio.")

        self.dominios = [dominio.strip().lower() for dominio in dominios if dominio.strip()]

        if not self.dominios:
            raise ValueError("O afiliador Amazon precisa " "possuir pelo menos um dominio.")

        self.repository = repository or LinksAfiliadosAmazonRepository()

    @property
    def nome(
        self,
    ) -> str:
        return self._nome

    def suporta(
        self,
        link: str,
    ) -> bool:
        host = (urlparse(link).hostname or "").lower()

        if host.startswith("www."):
            host = host[4:]

        for dominio in self.dominios:
            dominio_normalizado = dominio

            if dominio_normalizado.startswith("www."):
                dominio_normalizado = dominio_normalizado[4:]

            if host == dominio_normalizado or host.endswith(f".{dominio_normalizado}"):
                return True

        return False

    def gerar_link(
        self,
        link_original: str,
    ) -> str:
        if not self.suporta(link_original):
            raise ValueError("O link informado nao pertence " "a um dominio Amazon configurado.")

        link_afiliado = self.repository.obter_link_afiliado(link_original)

        if not link_afiliado:
            logger.warning(
                "Oferta Amazon sem link SiteStripe "
                "cadastrado. A publicacao permanecera "
                "bloqueada."
            )

            return link_original

        return link_afiliado
