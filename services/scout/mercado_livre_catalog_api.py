# 63.8738, -149.7525

from __future__ import annotations

import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv, set_key


class ErroApiMercadoLivre(RuntimeError):
    def __init__(
        self,
        motivo: str,
        *,
        status_code: int | None = None,
        transitorio: bool = False,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(motivo)
        self.motivo = str(motivo or "").strip() or "erro_api_mercado_livre"
        self.status_code = status_code
        self.transitorio = bool(transitorio)
        self.retry_after = (
            retry_after
            if isinstance(retry_after, int)
            and not isinstance(retry_after, bool)
            and retry_after >= 1
            else None
        )


@dataclass(frozen=True, slots=True)
class SnapshotCatalogoMercadoLivre:
    product_id: str
    item_id: str
    titulo: str
    preco: float
    currency_id: str
    seller_id: int | str | None
    permalink: str | None = None

    def como_snapshot_validacao(self) -> dict[str, Any]:
        return {
            "titulo": self.titulo,
            "preco_oficial": self.preco,
            "preco_original": None,
            "tipo_preco": "catalog_api_listing",
            "preco_parcelado": None,
            "valor_parcela": None,
            "parcelas": None,
            "disponivel": None,
            "preco_valido_ate": None,
            "mercado_livre_product_id": self.product_id,
            "mercado_livre_item_id": self.item_id,
            "mercado_livre_currency_id": self.currency_id,
            "mercado_livre_seller_id": self.seller_id,
        }


@dataclass(frozen=True, slots=True)
class DominioCatalogoMercadoLivre:
    domain_id: str
    domain_name: str
    category_id: str
    category_name: str


@dataclass(frozen=True, slots=True)
class ProdutoCatalogoMercadoLivre:
    product_id: str
    titulo: str
    domain_id: str
    status: str


class ClienteCatalogoMercadoLivre:
    BASE_URL = "https://api.mercadolibre.com"
    TOKEN_URL = f"{BASE_URL}/oauth/token"

    def __init__(
        self,
        *,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
        token_expires_at: int | float | str | None = None,
        env_path: str | Path | None = None,
        session=None,
        timeout: float = 20.0,
        agora: Callable[[], float] | None = None,
        persistir_tokens: bool = True,
    ) -> None:
        self._env_path = Path(env_path) if env_path is not None else self._env_padrao()

        if self._env_path.exists():
            load_dotenv(self._env_path, override=False)

        self._client_id = self._texto(
            client_id if client_id is not None else os.getenv("MERCADO_LIVRE_CLIENT_ID")
        )
        self._client_secret = self._texto(
            client_secret if client_secret is not None else os.getenv("MERCADO_LIVRE_CLIENT_SECRET")
        )
        self._access_token = self._texto(
            access_token if access_token is not None else os.getenv("MERCADO_LIVRE_ACCESS_TOKEN")
        )
        self._refresh_token = self._texto(
            refresh_token if refresh_token is not None else os.getenv("MERCADO_LIVRE_REFRESH_TOKEN")
        )

        expira = (
            token_expires_at
            if token_expires_at is not None
            else os.getenv("MERCADO_LIVRE_TOKEN_EXPIRES_AT")
        )
        self._token_expires_at = self._inteiro_ou_zero(expira)

        self._session = session or requests.Session()
        self._timeout = max(float(timeout), 1.0)
        self._agora = agora or time.time
        self._persistir_tokens = bool(persistir_tokens)

    def descobrir_dominios(
        self,
        consulta: str,
        limite: int = 3,
    ) -> tuple[DominioCatalogoMercadoLivre, ...]:
        consulta = self._texto(consulta)

        if not consulta:
            raise ValueError("consulta de dominio nao pode ser vazia.")

        limite = self._validar_limite_busca(limite)

        query = urlencode(
            {
                "q": consulta,
                "limit": limite,
            }
        )

        resposta = self._request_autenticado(
            "GET",
            (f"{self.BASE_URL}" "/sites/MLB/domain_discovery/search" f"?{query}"),
        )

        try:
            payload = resposta.json()
        except ValueError as erro:
            raise ErroApiMercadoLivre(
                "domain_discovery_ml_json_invalido",
                status_code=resposta.status_code,
                transitorio=True,
            ) from erro

        if not isinstance(payload, list):
            raise ErroApiMercadoLivre(
                "domain_discovery_ml_resposta_invalida",
                status_code=resposta.status_code,
                transitorio=True,
            )

        dominios: list[DominioCatalogoMercadoLivre] = []

        for item in payload:
            if not isinstance(item, dict):
                continue

            domain_id = self._texto(item.get("domain_id")).upper()

            if not domain_id:
                continue

            dominios.append(
                DominioCatalogoMercadoLivre(
                    domain_id=domain_id,
                    domain_name=self._texto(item.get("domain_name")),
                    category_id=self._texto(item.get("category_id")).upper(),
                    category_name=self._texto(item.get("category_name")),
                )
            )

        return tuple(dominios)

    def buscar_produtos(
        self,
        consulta: str,
        *,
        domain_id: str | None = None,
        limite: int = 5,
    ) -> tuple[ProdutoCatalogoMercadoLivre, ...]:
        consulta = self._texto(consulta)

        if not consulta:
            raise ValueError("consulta de produtos nao pode ser vazia.")

        limite = self._validar_limite_busca(limite)

        dominio = self._texto(domain_id).upper()

        parametros: dict[str, object] = {
            "status": "active",
            "site_id": "MLB",
            "q": consulta,
            "limit": limite,
        }

        if dominio:
            parametros["domain_id"] = dominio

        query = urlencode(parametros)

        resposta = self._request_autenticado(
            "GET",
            (f"{self.BASE_URL}" "/products/search" f"?{query}"),
        )

        try:
            payload = resposta.json()
        except ValueError as erro:
            raise ErroApiMercadoLivre(
                "products_search_ml_json_invalido",
                status_code=resposta.status_code,
                transitorio=True,
            ) from erro

        if not isinstance(payload, dict):
            raise ErroApiMercadoLivre(
                "products_search_ml_resposta_invalida",
                status_code=resposta.status_code,
                transitorio=True,
            )

        resultados = payload.get("results")

        if not isinstance(resultados, list):
            raise ErroApiMercadoLivre(
                "products_search_ml_results_invalidos",
                status_code=resposta.status_code,
                transitorio=True,
            )

        produtos: list[ProdutoCatalogoMercadoLivre] = []

        for item in resultados:
            if not isinstance(item, dict):
                continue

            product_id = self._texto(item.get("id")).upper()

            titulo = self._texto(item.get("name"))

            if not product_id or not titulo:
                continue

            produtos.append(
                ProdutoCatalogoMercadoLivre(
                    product_id=product_id,
                    titulo=titulo,
                    domain_id=self._texto(item.get("domain_id")).upper(),
                    status=self._texto(item.get("status")).casefold(),
                )
            )

        return tuple(produtos)

    def consultar_snapshot(
        self,
        product_id: str,
    ) -> SnapshotCatalogoMercadoLivre | None:
        product_id = self._validar_product_id(product_id)

        produto = self._get_json(
            f"/products/{product_id}",
        )

        titulo = self._texto(produto.get("name"))

        if not titulo:
            raise ErroApiMercadoLivre(
                "produto_catalogo_ml_sem_titulo",
                transitorio=False,
            )

        itens = self._get_json(
            f"/products/{product_id}/items",
        )

        resultados = itens.get("results")

        if not isinstance(resultados, list):
            raise ErroApiMercadoLivre(
                "resposta_items_catalogo_ml_invalida",
                transitorio=True,
            )

        candidatos = []

        for item in resultados:
            if not isinstance(item, dict):
                continue

            item_id = self._texto(item.get("item_id"))
            currency_id = self._texto(item.get("currency_id")).upper()
            preco = self._preco(item.get("price"))

            quantidade = item.get("available_quantity")

            if quantidade is not None:
                try:
                    if float(quantidade) <= 0:
                        continue
                except (TypeError, ValueError):
                    pass

            if not item_id or currency_id != "BRL" or preco is None:
                continue

            candidatos.append(
                (
                    preco,
                    item_id,
                    item.get("seller_id"),
                    currency_id,
                )
            )

        if not candidatos:
            return None

        preco, item_id, seller_id, currency_id = min(
            candidatos,
            key=lambda valor: (valor[0], valor[1]),
        )

        return SnapshotCatalogoMercadoLivre(
            product_id=product_id,
            item_id=item_id,
            titulo=titulo,
            preco=preco,
            currency_id=currency_id,
            seller_id=seller_id,
            permalink=(self._texto(produto.get("permalink")) or None),
        )

    def _get_json(
        self,
        caminho: str,
    ) -> dict[str, Any]:
        resposta = self._request_autenticado(
            "GET",
            f"{self.BASE_URL}{caminho}",
        )

        try:
            payload = resposta.json()
        except ValueError as erro:
            raise ErroApiMercadoLivre(
                "resposta_json_ml_invalida",
                status_code=resposta.status_code,
                transitorio=True,
            ) from erro

        if not isinstance(payload, dict):
            raise ErroApiMercadoLivre(
                "resposta_json_ml_nao_objeto",
                status_code=resposta.status_code,
                transitorio=True,
            )

        return payload

    def _request_autenticado(
        self,
        metodo: str,
        url: str,
    ):
        self._garantir_access_token()

        resposta = self._request(
            metodo,
            url,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
            },
        )

        if resposta.status_code == 401:
            self._renovar_token()

            resposta = self._request(
                metodo,
                url,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Accept": "application/json",
                },
            )

        self._validar_status(resposta)

        return resposta

    def _garantir_access_token(self) -> None:
        if not self._access_token:
            self._renovar_token()
            return

        if self._token_expires_at > 0 and self._token_expires_at <= int(self._agora()) + 60:
            self._renovar_token()

    def _renovar_token(self) -> None:
        if not self._client_id:
            raise ErroApiMercadoLivre(
                "mercado_livre_client_id_ausente",
                transitorio=False,
            )

        if not self._client_secret:
            raise ErroApiMercadoLivre(
                "mercado_livre_client_secret_ausente",
                transitorio=False,
            )

        if not self._refresh_token:
            raise ErroApiMercadoLivre(
                "mercado_livre_refresh_token_ausente",
                transitorio=False,
            )

        resposta = self._request(
            "POST",
            self.TOKEN_URL,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            },
        )

        if resposta.status_code != 200:
            self._validar_status(
                resposta,
                prefixo="falha_refresh_token_ml",
            )

        try:
            payload = resposta.json()
        except ValueError as erro:
            raise ErroApiMercadoLivre(
                "refresh_token_ml_json_invalido",
                status_code=resposta.status_code,
                transitorio=True,
            ) from erro

        access_token = self._texto(payload.get("access_token"))
        refresh_token = self._texto(payload.get("refresh_token"))

        try:
            expires_in = max(int(payload.get("expires_in") or 0), 0)
        except (TypeError, ValueError):
            expires_in = 0

        if not access_token:
            raise ErroApiMercadoLivre(
                "refresh_token_ml_sem_access_token",
                status_code=resposta.status_code,
                transitorio=True,
            )

        self._access_token = access_token

        if refresh_token:
            self._refresh_token = refresh_token

        self._token_expires_at = int(self._agora()) + expires_in if expires_in > 0 else 0

        if self._persistir_tokens:
            self._persistir_tokens_env()

    def _request(
        self,
        metodo: str,
        url: str,
        **kwargs,
    ):
        try:
            return self._session.request(
                metodo,
                url,
                timeout=self._timeout,
                **kwargs,
            )
        except requests.RequestException as erro:
            raise ErroApiMercadoLivre(
                "falha_rede_api_mercado_livre",
                transitorio=True,
            ) from erro

    @staticmethod
    def _validar_status(
        resposta,
        *,
        prefixo: str = "api_mercado_livre",
    ) -> None:
        status = int(resposta.status_code)

        if 200 <= status < 300:
            return

        transitorio = status == 429 or status >= 500
        retry_after: int | None = None

        if status == 429:
            headers = getattr(resposta, "headers", {}) or {}
            valor_retry_after = headers.get("Retry-After")

            if valor_retry_after is not None:
                try:
                    retry_after = max(
                        1,
                        int(valor_retry_after),
                    )
                except (TypeError, ValueError):
                    retry_after = None

        if status == 404:
            motivo = f"{prefixo}_nao_encontrado"
        elif status == 401:
            motivo = f"{prefixo}_nao_autorizado"
        elif status == 403:
            motivo = f"{prefixo}_acesso_negado"
        elif status == 429:
            motivo = f"{prefixo}_rate_limit"
        elif status >= 500:
            motivo = f"{prefixo}_indisponivel"
        else:
            motivo = f"{prefixo}_http_{status}"

        raise ErroApiMercadoLivre(
            motivo,
            status_code=status,
            transitorio=transitorio,
            retry_after=retry_after,
        )

    def _persistir_tokens_env(self) -> None:
        if not self._env_path.exists():
            return

        valores = {
            "MERCADO_LIVRE_ACCESS_TOKEN": self._access_token,
            "MERCADO_LIVRE_REFRESH_TOKEN": self._refresh_token,
            "MERCADO_LIVRE_TOKEN_EXPIRES_AT": str(self._token_expires_at),
        }

        for chave, valor in valores.items():
            set_key(
                str(self._env_path),
                chave,
                str(valor or ""),
                quote_mode="never",
            )

    @staticmethod
    def _env_padrao() -> Path:
        return Path(__file__).resolve().parents[2] / ".env"

    @staticmethod
    def _validar_product_id(valor: str) -> str:
        product_id = str(valor or "").strip().upper()

        if not re.fullmatch(r"MLB\d+", product_id):
            raise ErroApiMercadoLivre(
                "mercado_livre_product_id_invalido",
                transitorio=False,
            )

        return product_id

    @staticmethod
    def _validar_limite_busca(
        valor: object,
        *,
        maximo: int = 50,
    ) -> int:
        if isinstance(valor, bool) or not isinstance(valor, int) or valor <= 0:
            raise ValueError("limite de busca precisa ser inteiro positivo.")

        return min(
            valor,
            maximo,
        )

    @staticmethod
    def _texto(valor: object) -> str:
        return str(valor or "").strip()

    @staticmethod
    def _preco(valor: object) -> float | None:
        try:
            preco = float(valor)
        except (TypeError, ValueError):
            return None

        if preco <= 0:
            return None

        return round(preco, 2)

    @staticmethod
    def _inteiro_ou_zero(valor: object) -> int:
        try:
            return max(int(float(valor)), 0)
        except (TypeError, ValueError):
            return 0
