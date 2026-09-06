# 63.8738, -149.7525

from __future__ import annotations

import os
from datetime import date

import requests

from models.sinal_scout import SinalScout


class AwinPromotionsSensor:
    """Sensor oficial da Offers/Promotions API da Awin."""

    ENDPOINT = "https://api.awin.com/" "publisher/{publisher_id}/promotions"

    nome = "awin_promotions"

    def __init__(
        self,
        publisher_id: str | None = None,
        api_token: str | None = None,
        advertiser_ids: list[int] | None = None,
        page_size: int = 100,
        max_pages: int = 10,
        timeout_segundos: float = 30.0,
    ) -> None:
        if publisher_id is None:
            publisher_id = os.getenv(
                "AWIN_PUBLISHER_ID",
                "",
            )

        if api_token is None:
            api_token = os.getenv(
                "AWIN_API_TOKEN",
                "",
            )

        self.publisher_id = str(publisher_id).strip()

        self.api_token = str(api_token).strip()

        self.advertiser_ids = [int(valor) for valor in (advertiser_ids or [])]

        self.page_size = min(
            max(int(page_size), 10),
            200,
        )

        self.max_pages = max(
            int(max_pages),
            1,
        )

        self.timeout_segundos = max(
            float(timeout_segundos),
            1.0,
        )

    def buscar_sinais(
        self,
        updated_since: date | None = None,
    ) -> list[SinalScout]:
        self._validar_configuracao()

        sinais: list[SinalScout] = []

        for pagina in range(
            1,
            self.max_pages + 1,
        ):
            resposta = requests.post(
                self.ENDPOINT.format(
                    publisher_id=self.publisher_id,
                ),
                headers={
                    "Authorization": (f"Bearer {self.api_token}"),
                    "Content-Type": "application/json",
                },
                json=self._criar_payload(
                    pagina=pagina,
                    updated_since=updated_since,
                ),
                timeout=self.timeout_segundos,
            )

            resposta.raise_for_status()

            dados = resposta.json()

            if not isinstance(dados, dict):
                raise ValueError("Awin Promotions retornou " "estrutura inesperada.")

            itens = dados.get(
                "data",
                [],
            )

            if not isinstance(itens, list):
                raise ValueError("Awin Promotions nao retornou " "a lista 'data'.")

            for item in itens:
                sinal = self._converter_item(item)

                if sinal is not None:
                    sinais.append(sinal)

            if len(itens) < self.page_size:
                break

        return sinais

    def _criar_payload(
        self,
        pagina: int,
        updated_since: date | None,
    ) -> dict:
        filtros: dict = {
            "membership": "joined",
            "regionCodes": ["BR"],
            "status": "active",
            "type": "all",
        }

        if self.advertiser_ids:
            filtros["advertiserIds"] = self.advertiser_ids

        if updated_since is not None:
            filtros["updatedSince"] = updated_since.isoformat()

        return {
            "filters": filtros,
            "pagination": {
                "page": pagina,
                "pageSize": self.page_size,
            },
        }

    @staticmethod
    def _converter_item(
        item,
    ) -> SinalScout | None:
        if not isinstance(item, dict):
            return None

        promotion_id = item.get("promotionId")

        titulo = str(item.get("title") or "").strip()

        url = str(item.get("url") or "").strip()

        if promotion_id is None or not titulo or not url:
            return None

        advertiser = item.get("advertiser") or {}

        if not isinstance(
            advertiser,
            dict,
        ):
            advertiser = {}

        if advertiser.get("joined") is False:
            return None

        voucher = item.get("voucher") or {}

        if not isinstance(
            voucher,
            dict,
        ):
            voucher = {}

        return SinalScout(
            fonte="awin",
            id_externo=str(promotion_id),
            tipo=str(item.get("type") or "promotion"),
            titulo=titulo,
            url=url,
            advertiser_id=(str(advertiser.get("id") or "").strip() or None),
            advertiser_nome=(str(advertiser.get("name") or "").strip() or None),
            descricao=str(item.get("description") or "").strip(),
            termos=str(item.get("terms") or "").strip(),
            url_tracking=(str(item.get("urlTracking") or "").strip() or None),
            codigo_voucher=(str(voucher.get("code") or "").strip() or None),
            inicio=(str(item.get("startDate") or "").strip() or None),
            fim=(str(item.get("endDate") or "").strip() or None),
            regioes=(AwinPromotionsSensor._extrair_regioes(item.get("regions"))),
        )

    @staticmethod
    def _extrair_regioes(
        valor,
    ) -> tuple[str, ...]:
        if not isinstance(valor, dict):
            return ()

        if valor.get("all") is True:
            return ("ALL",)

        lista = valor.get(
            "list",
            [],
        )

        if not isinstance(lista, list):
            return ()

        codigos = []

        for item in lista:
            if not isinstance(
                item,
                dict,
            ):
                continue

            codigo = str(item.get("countryCode") or "").strip().upper()

            if codigo:
                codigos.append(codigo)

        return tuple(dict.fromkeys(codigos))

    def _validar_configuracao(
        self,
    ) -> None:
        if not self.publisher_id or not self.publisher_id.isdigit():
            raise ValueError("AWIN_PUBLISHER_ID ausente " "ou invalido.")

        if not self.api_token:
            raise ValueError("AWIN_API_TOKEN ausente.")
