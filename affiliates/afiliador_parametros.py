from urllib.parse import (
    parse_qsl,
    urlencode,
    urlparse,
    urlunparse
)

from affiliates.base_afiliador import BaseAfiliador


class AfiliadorParametros(BaseAfiliador):

    def __init__(
        self,
        nome: str,
        dominios: list[str],
        parametros: dict[str, str]
    ) -> None:
        nome_normalizado = nome.strip()

        if not nome_normalizado:
            raise ValueError(
                "O nome do afiliador não pode ficar vazio."
            )

        if not dominios:
            raise ValueError(
                "O afiliador precisa possuir pelo menos um domínio."
            )

        self._nome = nome_normalizado

        self.dominios = [
            dominio.strip().lower()
            for dominio in dominios
            if dominio.strip()
        ]

        if not self.dominios:
            raise ValueError(
                "O afiliador precisa possuir pelo menos um domínio válido."
            )

        self.parametros = parametros.copy()

    @property
    def nome(self) -> str:
        return self._nome

    def suporta(
        self,
        link: str
    ) -> bool:
        dominio_link = urlparse(
            link
        ).netloc.lower()

        if dominio_link.startswith(
            "www."
        ):
            dominio_link = dominio_link[
                4:
            ]

        for dominio in self.dominios:
            dominio_normalizado = dominio

            if dominio_normalizado.startswith(
                "www."
            ):
                dominio_normalizado = dominio_normalizado[
                    4:
                ]

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
        link_original: str
    ) -> str:
        partes_link = urlparse(
            link_original
        )

        parametros_existentes = dict(
            parse_qsl(
                partes_link.query,
                keep_blank_values=True
            )
        )

        parametros_existentes.update(
            self.parametros
        )

        nova_query = urlencode(
            parametros_existentes
        )

        return urlunparse(
            partes_link._replace(
                query=nova_query
            )
        )