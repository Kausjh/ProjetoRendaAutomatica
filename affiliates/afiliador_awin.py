import os
from urllib.parse import urlencode, urlparse

from affiliates.base_afiliador import BaseAfiliador

# 63.8738, -149.7525


class AfiliadorAwin(BaseAfiliador):
    ENDPOINT = "https://www.awin1.com/cread.php"

    def __init__(
        self,
        nome: str,
        dominios: list[str],
        advertiser_id: str,
        publisher_id: str | None = None,
    ) -> None:
        self._nome = nome.strip()

        if not self._nome:
            raise ValueError("O nome do afiliador Awin nao pode ficar vazio.")

        self.dominios = [dominio.strip().lower() for dominio in dominios if dominio.strip()]

        if not self.dominios:
            raise ValueError("O afiliador Awin precisa possuir pelo menos um dominio.")

        self.advertiser_id = str(advertiser_id).strip()

        if not self.advertiser_id or not self.advertiser_id.isdigit():
            raise ValueError("O advertiser_id da Awin precisa ser numerico.")

        if publisher_id is None:
            publisher_id = os.getenv(
                "AWIN_PUBLISHER_ID",
                "",
            )

        self.publisher_id = str(publisher_id).strip()

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

    def gerar_link(
        self,
        link_original: str,
    ) -> str:
        if not self.publisher_id or not self.publisher_id.isdigit():
            raise ValueError("AWIN_PUBLISHER_ID nao esta configurado " "ou nao e numerico.")

        if not self.suporta(link_original):
            raise ValueError(
                "O link informado nao pertence a um " "dominio configurado para este afiliador."
            )

        parametros = urlencode(
            {
                "awinmid": self.advertiser_id,
                "awinaffid": self.publisher_id,
                "ued": link_original,
            }
        )

        return f"{self.ENDPOINT}?{parametros}"
