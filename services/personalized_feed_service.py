from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from models.personalized_feed import (
    ItemFeedPersonalizado,
    PaginaFeedPersonalizado,
)

SCORE_WATCHLIST = 100
SCORE_PRECO_ALVO_ATINGIDO = 40
SCORE_MARKETPLACE_PREFERIDO = 25

MOTIVO_WATCHLIST = "watchlist"
MOTIVO_PRECO_ALVO_ATINGIDO = "preco_alvo_atingido"
MOTIVO_MARKETPLACE_PREFERIDO = "marketplace_preferido"


class PersonalizedFeedService:
    def __init__(
        self,
        *,
        catalogo_repository: object,
        price_intelligence_repository: object,
        user_personalization_service: object,
        tamanho_lote_catalogo: int = 200,
    ) -> None:
        self.catalogo_repository = catalogo_repository
        self.price_intelligence_repository = price_intelligence_repository
        self.user_personalization_service = user_personalization_service
        self.tamanho_lote_catalogo = max(
            1,
            min(int(tamanho_lote_catalogo), 200),
        )

    @staticmethod
    def _valor(objeto: object, campo: str, padrao: Any = None) -> Any:
        if isinstance(objeto, Mapping):
            return objeto.get(campo, padrao)
        return getattr(objeto, campo, padrao)

    @staticmethod
    def _decimal(valor: object) -> Decimal | None:
        if valor is None or isinstance(valor, bool):
            return None

        try:
            numero = Decimal(str(valor))
        except (InvalidOperation, ValueError):
            return None

        if not numero.is_finite() or numero <= 0:
            return None

        return numero

    @staticmethod
    def _timestamp(valor: object) -> float:
        texto = str(valor or "").strip()

        if not texto:
            return float("-inf")

        try:
            data = datetime.fromisoformat(texto.replace("Z", "+00:00"))
        except ValueError:
            return float("-inf")

        if data.tzinfo is None:
            data = data.replace(tzinfo=UTC)

        return data.timestamp()

    def _coletar_produtos(self) -> list[object]:
        produtos: list[object] = []
        offset = 0

        while True:
            lote = self.catalogo_repository.listar_produtos(
                limite=self.tamanho_lote_catalogo,
                offset=offset,
            )

            if not lote:
                break

            produtos.extend(lote)

            if len(lote) < self.tamanho_lote_catalogo:
                break

            offset += len(lote)

        return produtos

    def _precos_atuais(
        self,
        canonical_key: str,
    ) -> list[tuple[Decimal, str, str | None]]:
        itens = self.price_intelligence_repository.listar_precos_atuais(canonical_key)

        resultado: list[tuple[Decimal, str, str | None]] = []

        for item in itens:
            preco = self._decimal(self._valor(item, "preco_atual"))

            marketplace = str(self._valor(item, "marketplace") or "").strip().lower()

            identificador_raw = self._valor(
                item,
                "identificador",
            )

            identificador = (
                str(identificador_raw).strip() if identificador_raw is not None else None
            )

            if preco is None or not marketplace:
                continue

            resultado.append(
                (
                    preco,
                    marketplace,
                    identificador,
                )
            )

        return sorted(
            resultado,
            key=lambda item: (
                item[0],
                item[1],
                item[2] or "",
            ),
        )

    def _link_anuncio(
        self,
        produto: object,
        *,
        marketplace: str | None,
        identificador: str | None,
    ) -> str | None:
        anuncios = (
            self._valor(
                produto,
                "anuncios",
                (),
            )
            or ()
        )

        if marketplace and identificador:
            for anuncio in anuncios:
                if (
                    str(self._valor(anuncio, "marketplace") or "").strip().lower() == marketplace
                    and str(self._valor(anuncio, "identificador") or "").strip() == identificador
                ):
                    link = str(self._valor(anuncio, "link") or "").strip()
                    return link or None

        if marketplace:
            for anuncio in anuncios:
                if str(self._valor(anuncio, "marketplace") or "").strip().lower() == marketplace:
                    link = str(self._valor(anuncio, "link") or "").strip()
                    return link or None

        return None

    def _atualizado_em(
        self,
        produto: object,
        canonical_key: str,
    ) -> str:
        snapshot = self.price_intelligence_repository.obter_snapshot(canonical_key)

        if snapshot is not None:
            atualizado = str(self._valor(snapshot, "atualizado_em") or "").strip()

            if atualizado:
                return atualizado

        return str(self._valor(produto, "atualizado_em") or "").strip()

    def gerar(
        self,
        *,
        conta_id: str,
        limite: int = 20,
        offset: int = 0,
    ) -> PaginaFeedPersonalizado:
        limite_norm = max(1, min(int(limite), 50))
        offset_norm = max(0, int(offset))

        preferencias = self.user_personalization_service.obter_preferencias(conta_id)

        watchlist = self.user_personalization_service.listar_watchlist(conta_id)

        watchlist_por_chave = {str(item.canonical_key): item for item in watchlist}

        marketplaces_preferidos = {
            str(marketplace).strip().lower()
            for marketplace in preferencias.marketplaces_preferidos
            if str(marketplace).strip()
        }

        deduplicados: dict[str, ItemFeedPersonalizado] = {}

        for produto in self._coletar_produtos():
            canonical_key = str(self._valor(produto, "chave_canonica") or "").strip()

            if not canonical_key:
                continue

            item_watchlist = watchlist_por_chave.get(canonical_key)

            precos = self._precos_atuais(canonical_key)

            melhor_preco = precos[0] if precos else None

            preco_atual = melhor_preco[0] if melhor_preco is not None else None

            marketplace = melhor_preco[1] if melhor_preco is not None else None

            identificador = melhor_preco[2] if melhor_preco is not None else None

            score = 0
            motivos: list[str] = []

            preco_alvo = None

            if item_watchlist is not None:
                score += SCORE_WATCHLIST
                motivos.append(MOTIVO_WATCHLIST)

                preco_alvo = self._decimal(item_watchlist.preco_alvo)

                if preco_alvo is not None and preco_atual is not None and preco_atual <= preco_alvo:
                    score += SCORE_PRECO_ALVO_ATINGIDO
                    motivos.append(MOTIVO_PRECO_ALVO_ATINGIDO)

            if marketplace is not None and marketplace in marketplaces_preferidos:
                score += SCORE_MARKETPLACE_PREFERIDO
                motivos.append(MOTIVO_MARKETPLACE_PREFERIDO)

            if not motivos:
                continue

            atualizado_em = self._atualizado_em(
                produto,
                canonical_key,
            )

            item = ItemFeedPersonalizado(
                canonical_key=canonical_key,
                nome_canonico=str(
                    self._valor(
                        produto,
                        "nome_canonico",
                    )
                    or canonical_key
                ),
                categoria=self._valor(
                    produto,
                    "categoria",
                ),
                marca=self._valor(
                    produto,
                    "marca",
                ),
                modelo=self._valor(
                    produto,
                    "modelo",
                ),
                score_relevancia=score,
                motivos=tuple(motivos),
                em_watchlist=(item_watchlist is not None),
                preco_alvo=preco_alvo,
                preco_atual=preco_atual,
                marketplace=marketplace,
                identificador=identificador,
                link=self._link_anuncio(
                    produto,
                    marketplace=marketplace,
                    identificador=identificador,
                ),
                atualizado_em=atualizado_em,
            )

            existente = deduplicados.get(canonical_key)

            if existente is None:
                deduplicados[canonical_key] = item
                continue

            atual_key = (
                item.score_relevancia,
                self._timestamp(item.atualizado_em),
            )

            existente_key = (
                existente.score_relevancia,
                self._timestamp(existente.atualizado_em),
            )

            if atual_key > existente_key:
                deduplicados[canonical_key] = item

        ordenados = sorted(
            deduplicados.values(),
            key=lambda item: (
                -item.score_relevancia,
                -self._timestamp(item.atualizado_em),
                item.canonical_key,
            ),
        )

        pagina = ordenados[offset_norm : offset_norm + limite_norm]

        return PaginaFeedPersonalizado(
            total=len(ordenados),
            limite=limite_norm,
            offset=offset_norm,
            itens=tuple(pagina),
        )
