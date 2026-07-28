import logging
from urllib.parse import urlparse

from affiliates.base_afiliador import BaseAfiliador
from repositories.links_afiliados_mercado_livre_repository import (
    LinksAfiliadosMercadoLivreRepository,
)


logger = logging.getLogger(__name__)

# 63.8738, -149.7525


class AfiliadorMercadoLivre(BaseAfiliador):

    def __init__(
        self,
        nome: str,
        dominios: list[str],
        repository: LinksAfiliadosMercadoLivreRepository | None = None,
    ) -> None:
        nome_normalizado = nome.strip()

        if not nome_normalizado:
            raise ValueError(
                "O nome do afiliador do Mercado Livre não pode ficar vazio."
            )

        dominios_normalizados = [
            dominio.strip().lower()
            for dominio in dominios
            if dominio.strip()
        ]

        if not dominios_normalizados:
            raise ValueError(
                "O afiliador do Mercado Livre precisa possuir pelo menos um domínio."
            )

        self._nome = nome_normalizado
        self.dominios = dominios_normalizados
        self.repository = (
            repository
            or LinksAfiliadosMercadoLivreRepository()
        )

    @property
    def nome(self) -> str:
        return self._nome

    def suporta(
        self,
        link: str,
    ) -> bool:
        dominio_link = (
            urlparse(link).hostname
            or ""
        ).lower()

        if dominio_link.startswith("www."):
            dominio_link = dominio_link[4:]

        for dominio in self.dominios:
            dominio_normalizado = dominio

            if dominio_normalizado.startswith("www."):
                dominio_normalizado = dominio_normalizado[4:]

            if (
                dominio_link == dominio_normalizado
                or dominio_link.endswith(
                    f".{dominio_normalizado}"
                )
            ):
                return True

        return False

    def gerar_link(
        self,
        link_original: str,
    ) -> str:
        link_afiliado = (
            self.repository.obter_link_afiliado(
                link_original
            )
        )

        if not link_afiliado:
            logger.warning(
                "Não foi possível gerar link afiliado do Mercado Livre. "
                "O link original será mantido: %s",
                link_original,
            )

            return link_original

        logger.info(
            "Link afiliado do Mercado Livre pronto: %s",
            link_afiliado,
        )

        return link_afiliado
