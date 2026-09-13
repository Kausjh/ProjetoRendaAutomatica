from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

from repositories.alert_engine_repository import AlertEngineRepository
from repositories.catalogo_canonico_repository import CatalogoCanonicoRepository
from repositories.price_intelligence_repository import PriceIntelligenceRepository

API_VERSION = "v1"


class ControladorApiAplicacao:
    def __init__(
        self,
        *,
        catalogo_repository: CatalogoCanonicoRepository | None = None,
        price_intelligence_repository: PriceIntelligenceRepository | None = None,
        alert_engine_repository: AlertEngineRepository | None = None,
    ) -> None:
        self.catalogo_repository = catalogo_repository or CatalogoCanonicoRepository()
        self.price_intelligence_repository = (
            price_intelligence_repository or PriceIntelligenceRepository()
        )
        self.alert_engine_repository = alert_engine_repository or AlertEngineRepository()

    @staticmethod
    def _serializar(valor: Any) -> Any:
        if is_dataclass(valor) and not isinstance(valor, type):
            return ControladorApiAplicacao._serializar(asdict(valor))

        if isinstance(valor, Mapping):
            return {
                str(chave): ControladorApiAplicacao._serializar(item)
                for chave, item in valor.items()
            }

        if isinstance(valor, Sequence) and not isinstance(
            valor,
            (str, bytes, bytearray),
        ):
            return [ControladorApiAplicacao._serializar(item) for item in valor]

        return valor

    @staticmethod
    def _normalizar_paginacao(
        *,
        limite: object,
        offset: object,
        limite_padrao: int = 50,
        limite_maximo: int = 200,
    ) -> tuple[int, int]:
        try:
            limite_norm = int(limite)
        except (TypeError, ValueError):
            limite_norm = limite_padrao

        try:
            offset_norm = int(offset)
        except (TypeError, ValueError):
            offset_norm = 0

        return (
            max(1, min(limite_norm, limite_maximo)),
            max(0, offset_norm),
        )

    def health(self) -> dict[str, object]:
        return {
            "status": "ok",
            "api_version": API_VERSION,
        }

    def listar_produtos(
        self,
        *,
        limite: object = 50,
        offset: object = 0,
    ) -> dict[str, object]:
        limite_norm, offset_norm = self._normalizar_paginacao(
            limite=limite,
            offset=offset,
        )
        produtos = self.catalogo_repository.listar_produtos(
            limite=limite_norm,
            offset=offset_norm,
        )

        return {
            "api_version": API_VERSION,
            "total": int(self.catalogo_repository.quantidade_produtos()),
            "limite": limite_norm,
            "offset": offset_norm,
            "itens": [self._resumo_produto(produto) for produto in produtos],
        }

    def obter_produto(
        self,
        chave_canonica: str,
    ) -> dict[str, object] | None:
        chave = str(chave_canonica or "").strip()
        if not chave:
            return None

        produto = self.catalogo_repository.obter_produto(chave)
        if produto is None:
            return None

        snapshot = self.price_intelligence_repository.obter_snapshot(chave)
        precos_atuais = self.price_intelligence_repository.listar_precos_atuais(chave)
        estado_alerta = self.alert_engine_repository.obter_estado_produto(chave)

        return {
            "api_version": API_VERSION,
            "produto": self._serializar(produto),
            "price_intelligence": self._serializar(snapshot),
            "precos_atuais": self._serializar(precos_atuais),
            "alert_engine": self._serializar(estado_alerta),
        }

    def listar_historico_produto(
        self,
        chave_canonica: str,
        *,
        limite: object = 50,
        offset: object = 0,
    ) -> dict[str, object] | None:
        chave = str(chave_canonica or "").strip()
        if not chave:
            return None

        if self.catalogo_repository.obter_produto(chave) is None:
            return None

        limite_norm, offset_norm = self._normalizar_paginacao(
            limite=limite,
            offset=offset,
        )
        itens = self.price_intelligence_repository.listar_historico_paginado(
            chave,
            limite=limite_norm,
            offset=offset_norm,
        )

        return {
            "api_version": API_VERSION,
            "chave_canonica": chave,
            "limite": limite_norm,
            "offset": offset_norm,
            "itens": self._serializar(itens),
        }

    def listar_alertas(
        self,
        *,
        limite: object = 50,
        offset: object = 0,
    ) -> dict[str, object]:
        limite_norm, offset_norm = self._normalizar_paginacao(
            limite=limite,
            offset=offset,
        )
        metricas = self.alert_engine_repository.obter_metricas()
        itens = self.alert_engine_repository.listar_eventos(
            limite=limite_norm,
            offset=offset_norm,
        )

        return {
            "api_version": API_VERSION,
            "total": int(metricas["eventos"]),
            "limite": limite_norm,
            "offset": offset_norm,
            "itens": self._serializar(itens),
        }

    def _resumo_produto(self, produto: object) -> dict[str, object]:
        serializado = self._serializar(produto)
        if not isinstance(serializado, dict):
            raise TypeError("Produto canonico nao serializavel como objeto JSON.")

        chave = str(serializado.get("chave_canonica") or "").strip()
        snapshot = self.price_intelligence_repository.obter_snapshot(chave) if chave else None

        preco = None
        if snapshot is not None:
            snapshot_dict = self._serializar(snapshot)
            preco = {
                "preco_minimo_atual": snapshot_dict.get("preco_minimo_atual"),
                "preco_maximo_atual": snapshot_dict.get("preco_maximo_atual"),
                "mediana_atual": snapshot_dict.get("mediana_atual"),
                "marketplace_melhor_preco": snapshot_dict.get("marketplace_melhor_preco"),
                "menor_preco_historico": snapshot_dict.get("menor_preco_historico"),
                "atualizado_em": snapshot_dict.get("atualizado_em"),
            }

        return {
            "chave_canonica": serializado.get("chave_canonica"),
            "nome_canonico": serializado.get("nome_canonico"),
            "categoria": serializado.get("categoria"),
            "marca": serializado.get("marca"),
            "modelo": serializado.get("modelo"),
            "confianca": serializado.get("confianca"),
            "preco": preco,
        }
