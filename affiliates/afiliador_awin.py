from __future__ import annotations

import hashlib
import logging
import os
from urllib.parse import urlencode, urlparse

import requests

from affiliates.base_afiliador import BaseAfiliador
from repositories.links_afiliados_awin_repository import (
    LinksAfiliadosAwinRepository,
)

# 63.8738, -149.7525

logger = logging.getLogger(__name__)


class AfiliadorAwin(BaseAfiliador):
    ENDPOINT = "https://www.awin1.com/cread.php"
    LINK_BUILDER_ENDPOINT = "https://api.awin.com/publishers/" "{publisher_id}/linkbuilder/generate"

    def __init__(
        self,
        nome: str,
        dominios: list[str],
        advertiser_id: str,
        publisher_id: str | None = None,
        api_token: str | None = None,
        repository: LinksAfiliadosAwinRepository | None = None,
        timeout_segundos: float = 15.0,
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

        if api_token is None:
            api_token = os.getenv(
                "AWIN_API_TOKEN",
                "",
            )

        self.api_token = str(api_token).strip()

        self.repository = repository or LinksAfiliadosAwinRepository()

        self.timeout_segundos = max(
            float(timeout_segundos),
            1.0,
        )

    @property
    def nome(self) -> str:
        return self._nome

    def suporta(
        self,
        link: str,
    ) -> bool:
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

        link_longo = self._gerar_link_longo(link_original)

        if not self.api_token:
            logger.info(
                "AWIN_API_TOKEN ausente para '%s'. " "Usando tracking link Awin tradicional.",
                self.nome,
            )
            return link_longo

        chave_cache = self._criar_chave_cache(link_original)

        try:
            link_cache = self.repository.obter(chave_cache)
        except Exception:
            logger.warning(
                "Falha ao consultar cache de short links Awin " "para '%s'.",
                self.nome,
                exc_info=True,
            )
            link_cache = None

        if link_cache and self._eh_short_link_valido(link_cache):
            logger.info(
                "Short link Awin recuperado do cache para '%s'.",
                self.nome,
            )
            return link_cache

        link_curto = self._solicitar_link_curto(link_original)

        if not link_curto:
            return link_longo

        try:
            self.repository.salvar(
                chave_cache,
                link_curto,
            )
        except Exception:
            logger.warning(
                "Short link Awin foi gerado, mas nao foi " "possivel salva-lo no cache para '%s'.",
                self.nome,
                exc_info=True,
            )

        logger.info(
            "Short link Awin pronto para '%s'.",
            self.nome,
        )

        return link_curto

    def _solicitar_link_curto(
        self,
        link_original: str,
    ) -> str | None:
        endpoint = self.LINK_BUILDER_ENDPOINT.format(
            publisher_id=self.publisher_id,
        )

        try:
            resposta = requests.post(
                endpoint,
                headers={
                    "Authorization": (f"Bearer {self.api_token}"),
                    "Content-Type": "application/json",
                },
                json={
                    "advertiserId": int(self.advertiser_id),
                    "destinationUrl": (link_original),
                    "shorten": True,
                },
                timeout=self.timeout_segundos,
            )
        except requests.RequestException:
            logger.warning(
                "Link Builder da Awin indisponivel para '%s'. " "Usando tracking link tradicional.",
                self.nome,
                exc_info=True,
            )
            return None

        if not resposta.ok:
            logger.warning(
                "Link Builder da Awin retornou HTTP %s "
                "para '%s'. Usando tracking link tradicional.",
                resposta.status_code,
                self.nome,
            )
            return None

        try:
            dados = resposta.json()
        except ValueError:
            logger.warning(
                "Link Builder da Awin retornou JSON invalido " "para '%s'.",
                self.nome,
            )
            return None

        link_curto = str(dados.get("shortUrl") or "").strip()

        if not self._eh_short_link_valido(link_curto):
            logger.warning(
                "Link Builder da Awin nao retornou "
                "um short link tidd.ly valido para '%s'. "
                "Usando tracking link tradicional.",
                self.nome,
            )
            return None

        return link_curto

    def _gerar_link_longo(
        self,
        link_original: str,
    ) -> str:
        parametros = urlencode(
            {
                "awinmid": self.advertiser_id,
                "awinaffid": self.publisher_id,
                "ued": link_original,
            }
        )

        return f"{self.ENDPOINT}" f"?{parametros}"

    def _criar_chave_cache(
        self,
        link_original: str,
    ) -> str:
        conteudo = f"{self.publisher_id}|" f"{self.advertiser_id}|" f"{link_original}"

        return hashlib.sha256(conteudo.encode("utf-8")).hexdigest()

    @staticmethod
    def _eh_short_link_valido(
        link: str,
    ) -> bool:
        if not isinstance(link, str):
            return False

        link = link.strip()

        if not link:
            return False

        parsed = urlparse(link)

        host = (parsed.hostname or "").lower()

        if host.startswith("www."):
            host = host[4:]

        return parsed.scheme == "https" and host == "tidd.ly" and bool(parsed.path.strip("/"))
