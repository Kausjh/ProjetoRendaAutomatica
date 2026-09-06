# 63.8738, -149.7525

from __future__ import annotations

import re
from urllib.parse import urlparse

import requests

from models.resolucao_scout import ResolucaoScout
from models.sinal_scout import SinalScout


class AwinDestinoResolver:
    """Resolve sinais Awin ate o destino oficial do marketplace."""

    nome = "awin_destino"

    DOMINIOS_MARKETPLACE = {
        "kabum.com.br": "kabum",
        "aliexpress.com": "aliexpress",
    }

    PADRAO_KABUM = re.compile(
        r"/produto/(\d+)(?:[/?]|$)",
        re.IGNORECASE,
    )

    PADRAO_ALIEXPRESS = re.compile(
        r"/item/(\d+)\.html(?:[/?]|$)",
        re.IGNORECASE,
    )

    def __init__(
        self,
        timeout_segundos: float = 15.0,
    ) -> None:
        self.timeout_segundos = max(
            float(timeout_segundos),
            1.0,
        )

    def suporta(
        self,
        sinal: SinalScout,
    ) -> bool:
        return str(sinal.fonte).strip().casefold() == "awin"

    def resolver(
        self,
        sinal: SinalScout,
    ) -> ResolucaoScout:
        if not self.suporta(sinal):
            return ResolucaoScout(
                fonte=sinal.fonte,
                id_externo=sinal.id_externo,
                status="nao_suportado",
                motivo="fonte_nao_suportada",
            )

        # Se a URL entregue pela Awin ja aponta
        # diretamente para um marketplace conhecido,
        # nenhuma requisicao extra e necessaria.
        direta = self._classificar_destino(
            sinal=sinal,
            url=sinal.url,
            http_status=None,
        )

        if direta is not None:
            return direta

        candidatos: list[str] = []

        for valor in (
            sinal.url_tracking,
            sinal.url,
        ):
            url = str(valor or "").strip()

            if url and url not in candidatos and self._eh_https(url):
                candidatos.append(url)

        if not candidatos:
            return ResolucaoScout(
                fonte=sinal.fonte,
                id_externo=sinal.id_externo,
                status="erro",
                motivo="nenhuma_url_https_valida",
            )

        ultima_url: str | None = None
        ultimo_status: int | None = None
        houve_resposta = False

        for candidato in candidatos:
            try:
                resposta = requests.get(
                    candidato,
                    allow_redirects=True,
                    stream=True,
                    timeout=self.timeout_segundos,
                    headers={"User-Agent": ("Mozilla/5.0 " "(Windows NT 10.0; " "Win64; x64)")},
                )

            except requests.RequestException:
                continue

            houve_resposta = True

            try:
                ultima_url = str(resposta.url).strip()

                valor_status = getattr(
                    resposta,
                    "status_code",
                    None,
                )

                if isinstance(
                    valor_status,
                    int,
                ):
                    ultimo_status = valor_status

            finally:
                resposta.close()

            resolucao = self._classificar_destino(
                sinal=sinal,
                url=ultima_url,
                http_status=(ultimo_status),
            )

            if resolucao is not None:
                return resolucao

        if houve_resposta:
            return ResolucaoScout(
                fonte=sinal.fonte,
                id_externo=sinal.id_externo,
                status="nao_suportado",
                tipo_destino="externo",
                url_destino=ultima_url,
                http_status=ultimo_status,
                motivo=("destino_fora_dos_" "marketplaces_suportados"),
            )

        return ResolucaoScout(
            fonte=sinal.fonte,
            id_externo=sinal.id_externo,
            status="erro",
            motivo="falha_ao_resolver_destino",
        )

    def _classificar_destino(
        self,
        sinal: SinalScout,
        url: str | None,
        http_status: int | None,
    ) -> ResolucaoScout | None:
        url = str(url or "").strip()

        if not self._eh_https(url):
            return None

        host = self._normalizar_host(urlparse(url).hostname)

        marketplace = self._identificar_marketplace(host)

        if marketplace is None:
            return None

        id_produto = self._extrair_id_produto(
            marketplace=marketplace,
            url=url,
        )

        if id_produto is not None:
            return ResolucaoScout(
                fonte=sinal.fonte,
                id_externo=sinal.id_externo,
                status="resolvido",
                marketplace=marketplace,
                tipo_destino="produto",
                url_destino=url,
                id_produto=id_produto,
                http_status=http_status,
                motivo="produto_identificado",
            )

        return ResolucaoScout(
            fonte=sinal.fonte,
            id_externo=sinal.id_externo,
            status="landing_page",
            marketplace=marketplace,
            tipo_destino="campanha",
            url_destino=url,
            http_status=http_status,
            motivo=("destino_oficial_sem_" "produto_especifico"),
        )

    @classmethod
    def _identificar_marketplace(
        cls,
        host: str,
    ) -> str | None:
        for (
            dominio,
            marketplace,
        ) in cls.DOMINIOS_MARKETPLACE.items():
            if host == dominio or host.endswith(f".{dominio}"):
                return marketplace

        return None

    @classmethod
    def _extrair_id_produto(
        cls,
        marketplace: str,
        url: str,
    ) -> str | None:
        caminho = urlparse(url).path or ""

        if marketplace == "kabum":
            correspondencia = cls.PADRAO_KABUM.search(caminho)

        elif marketplace == "aliexpress":
            correspondencia = cls.PADRAO_ALIEXPRESS.search(caminho)

        else:
            correspondencia = None

        if correspondencia is None:
            return None

        return str(correspondencia.group(1))

    @staticmethod
    def _eh_https(
        url: str,
    ) -> bool:
        try:
            parsed = urlparse(str(url).strip())

        except ValueError:
            return False

        return parsed.scheme.casefold() == "https" and bool(parsed.hostname)

    @staticmethod
    def _normalizar_host(
        host: str | None,
    ) -> str:
        valor = str(host or "").strip().casefold()

        if valor.startswith("www."):
            valor = valor[4:]

        return valor
