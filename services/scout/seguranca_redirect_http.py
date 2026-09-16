# 63.8738, -149.7525

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests


class UrlRedeNaoPermitida(ValueError):
    pass


@dataclass(frozen=True)
class ResultadoRedirectHttpSeguro:
    resposta: Any
    url_final: str
    urls_visitadas: tuple[str, ...]


def _host_corresponde(host: str, dominio: str) -> bool:
    return host == dominio or host.endswith("." + dominio)


def validar_url_http_permitida(
    url: str,
    *,
    dominios_permitidos: Iterable[str],
) -> str:
    texto = str(url or "").strip()

    if not texto:
        raise UrlRedeNaoPermitida("url_vazia")

    try:
        partes = urlsplit(texto)
    except ValueError as erro:
        raise UrlRedeNaoPermitida("url_invalida") from erro

    esquema = str(partes.scheme or "").casefold()

    if esquema not in {"http", "https"}:
        raise UrlRedeNaoPermitida("esquema_nao_permitido")

    if partes.username is not None or partes.password is not None:
        raise UrlRedeNaoPermitida("credenciais_na_url_nao_permitidas")

    host = str(partes.hostname or "").strip().rstrip(".").casefold()

    if not host:
        raise UrlRedeNaoPermitida("host_ausente")

    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise UrlRedeNaoPermitida("host_local_nao_permitido")

    try:
        porta = partes.port
    except ValueError as erro:
        raise UrlRedeNaoPermitida("porta_invalida") from erro

    if porta not in {None, 80, 443}:
        raise UrlRedeNaoPermitida("porta_nao_permitida")

    dominios = tuple(
        str(item or "").strip().rstrip(".").casefold()
        for item in dominios_permitidos
        if str(item or "").strip()
    )

    if not dominios:
        raise UrlRedeNaoPermitida("allowlist_vazia")

    if not any(_host_corresponde(host, dominio) for dominio in dominios):
        raise UrlRedeNaoPermitida("host_fora_da_allowlist")

    return texto


def resolver_redirects_requests(
    url: str,
    *,
    dominios_permitidos: Iterable[str],
    timeout_segundos: float,
    headers: dict[str, str] | None = None,
    stream: bool = False,
    max_redirects: int = 5,
    http_get: Callable[..., Any] | None = None,
) -> ResultadoRedirectHttpSeguro:
    if max_redirects < 0:
        raise ValueError("max_redirects precisa ser >= 0")

    get = http_get or requests.get
    atual = validar_url_http_permitida(
        url,
        dominios_permitidos=dominios_permitidos,
    )

    visitadas: list[str] = []
    status_redirect = {301, 302, 303, 307, 308}

    for salto in range(max_redirects + 1):
        resposta = get(
            atual,
            allow_redirects=False,
            timeout=float(timeout_segundos),
            headers=dict(headers or {}),
            stream=bool(stream),
        )

        visitadas.append(atual)

        status = getattr(resposta, "status_code", None)

        if status not in status_redirect:
            url_resposta = str(getattr(resposta, "url", "") or atual).strip()

            url_final = validar_url_http_permitida(
                url_resposta,
                dominios_permitidos=dominios_permitidos,
            )

            return ResultadoRedirectHttpSeguro(
                resposta=resposta,
                url_final=url_final,
                urls_visitadas=tuple(visitadas),
            )

        location = str(getattr(resposta, "headers", {}).get("Location") or "").strip()

        if not location:
            try:
                resposta.close()
            finally:
                raise UrlRedeNaoPermitida("redirect_sem_location")

        if salto >= max_redirects:
            try:
                resposta.close()
            finally:
                raise UrlRedeNaoPermitida("limite_redirects_excedido")

        proxima = urljoin(atual, location)

        proxima = validar_url_http_permitida(
            proxima,
            dominios_permitidos=dominios_permitidos,
        )

        resposta.close()
        atual = proxima

    raise UrlRedeNaoPermitida("limite_redirects_excedido")
