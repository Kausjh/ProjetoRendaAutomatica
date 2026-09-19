from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from services.personalized_feed_service import (
    MOTIVO_MARKETPLACE_PREFERIDO,
    MOTIVO_PRECO_ALVO_ATINGIDO,
    MOTIVO_WATCHLIST,
    PersonalizedFeedService,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "personalized_feed_v1.json"
DOC = ROOT / "docs" / "44-personalized-feed-v1.md"


@dataclass(frozen=True)
class AnuncioFake:
    marketplace: str
    identificador: str
    link: str


@dataclass(frozen=True)
class ProdutoFake:
    chave_canonica: str
    nome_canonico: str
    categoria: str = "hardware"
    marca: str = "marca"
    modelo: str = "modelo"
    atualizado_em: str = "2026-09-19T12:00:00-03:00"
    anuncios: tuple[AnuncioFake, ...] = ()


class CatalogoFake:
    def __init__(self, produtos):
        self.produtos = list(produtos)

    def listar_produtos(self, *, limite: int, offset: int):
        return self.produtos[offset : offset + limite]


class PriceFake:
    def __init__(self, precos=None, snapshots=None):
        self.precos = precos or {}
        self.snapshots = snapshots or {}

    def listar_precos_atuais(self, canonical_key: str):
        return list(self.precos.get(canonical_key, []))

    def obter_snapshot(self, canonical_key: str):
        atualizado = self.snapshots.get(canonical_key)

        if atualizado is None:
            return None

        return SimpleNamespace(
            atualizado_em=atualizado,
        )


class PersonalizacaoFake:
    def __init__(
        self,
        *,
        marketplaces=(),
        watchlist=(),
    ):
        self.preferencias = SimpleNamespace(
            marketplaces_preferidos=tuple(marketplaces),
        )
        self.watchlist = list(watchlist)

    def obter_preferencias(self, conta_id: str):
        assert conta_id
        return self.preferencias

    def listar_watchlist(self, conta_id: str):
        assert conta_id
        return list(self.watchlist)


def preco(
    valor: str,
    marketplace: str,
    identificador: str,
):
    return {
        "preco_atual": valor,
        "marketplace": marketplace,
        "identificador": identificador,
    }


def watchlist(
    canonical_key: str,
    preco_alvo: str | None = None,
):
    return SimpleNamespace(
        canonical_key=canonical_key,
        preco_alvo=(Decimal(preco_alvo) if preco_alvo is not None else None),
    )


def service(
    *,
    produtos,
    precos=None,
    snapshots=None,
    marketplaces=(),
    watchlist_itens=(),
):
    return PersonalizedFeedService(
        catalogo_repository=CatalogoFake(produtos),
        price_intelligence_repository=PriceFake(
            precos=precos,
            snapshots=snapshots,
        ),
        user_personalization_service=PersonalizacaoFake(
            marketplaces=marketplaces,
            watchlist=watchlist_itens,
        ),
    )


def test_contract_define_core_sem_http():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["personalized_feed_version"] == 1

    assert data["stage"] == "core-service"

    assert data["ranking"]["watchlist"] == 100

    assert data["ranking"]["target_price_reached"] == 40

    assert data["ranking"]["preferred_marketplace"] == 25

    boundaries = data["boundaries"]

    assert boundaries["new_http_routes"] is False

    assert boundaries["public_app_integration"] is False

    assert boundaries["push_delivery"] is False

    assert boundaries["notification_outbox_consumption"] is False


def test_watchlist_e_preco_alvo_tem_prioridade():
    gpu = ProdutoFake(
        "gpu",
        "GPU",
        anuncios=(
            AnuncioFake(
                "mercado_livre",
                "gpu-1",
                "https://example.test/gpu",
            ),
        ),
    )

    ssd = ProdutoFake(
        "ssd",
        "SSD",
        anuncios=(
            AnuncioFake(
                "shopee",
                "ssd-1",
                "https://example.test/ssd",
            ),
        ),
    )

    feed = service(
        produtos=[ssd, gpu],
        precos={
            "gpu": [
                preco(
                    "900.00",
                    "mercado_livre",
                    "gpu-1",
                )
            ],
            "ssd": [
                preco(
                    "500.00",
                    "shopee",
                    "ssd-1",
                )
            ],
        },
        marketplaces=("shopee",),
        watchlist_itens=(
            watchlist(
                "gpu",
                "950.00",
            ),
        ),
    ).gerar(
        conta_id="usr_1",
    )

    assert feed.total == 2

    assert [item.canonical_key for item in feed.itens] == [
        "gpu",
        "ssd",
    ]

    gpu_item = feed.itens[0]

    assert gpu_item.score_relevancia == 140

    assert MOTIVO_WATCHLIST in gpu_item.motivos

    assert MOTIVO_PRECO_ALVO_ATINGIDO in gpu_item.motivos

    assert gpu_item.preco_atual == Decimal("900.00")

    assert gpu_item.preco_alvo == Decimal("950.00")

    assert gpu_item.link == "https://example.test/gpu"

    ssd_item = feed.itens[1]

    assert ssd_item.score_relevancia == 25

    assert ssd_item.motivos == (MOTIVO_MARKETPLACE_PREFERIDO,)


def test_produto_sem_sinal_real_nao_entra():
    cpu = ProdutoFake(
        "cpu",
        "CPU",
    )

    feed = service(
        produtos=[cpu],
        precos={
            "cpu": [
                preco(
                    "1000.00",
                    "mercado_livre",
                    "cpu-1",
                )
            ]
        },
    ).gerar(
        conta_id="usr_1",
    )

    assert feed.total == 0
    assert feed.itens == ()


def test_recencia_desempata_mesmo_score():
    antigo = ProdutoFake(
        "antigo",
        "Antigo",
    )

    novo = ProdutoFake(
        "novo",
        "Novo",
    )

    feed = service(
        produtos=[antigo, novo],
        precos={
            "antigo": [
                preco(
                    "100.00",
                    "shopee",
                    "a",
                )
            ],
            "novo": [
                preco(
                    "100.00",
                    "shopee",
                    "n",
                )
            ],
        },
        snapshots={
            "antigo": ("2026-09-18T12:00:00-03:00"),
            "novo": ("2026-09-19T12:00:00-03:00"),
        },
        marketplaces=("shopee",),
    ).gerar(
        conta_id="usr_1",
    )

    assert [item.canonical_key for item in feed.itens] == [
        "novo",
        "antigo",
    ]


def test_deduplica_por_canonical_key_e_pagina_depois_do_ranking():
    a = ProdutoFake(
        "produto_a",
        "Produto A",
    )

    b = ProdutoFake(
        "produto_b",
        "Produto B",
    )

    feed_service = service(
        produtos=[a, a, b],
        precos={
            "produto_a": [
                preco(
                    "100.00",
                    "shopee",
                    "a",
                )
            ],
            "produto_b": [
                preco(
                    "200.00",
                    "shopee",
                    "b",
                )
            ],
        },
        marketplaces=("shopee",),
    )

    pagina_1 = feed_service.gerar(
        conta_id="usr_1",
        limite=1,
        offset=0,
    )

    pagina_2 = feed_service.gerar(
        conta_id="usr_1",
        limite=1,
        offset=1,
    )

    assert pagina_1.total == 2
    assert pagina_2.total == 2
    assert len(pagina_1.itens) == 1
    assert len(pagina_2.itens) == 1

    assert pagina_1.itens[0].canonical_key != pagina_2.itens[0].canonical_key


def test_limites_de_paginacao_sao_normalizados():
    produto = ProdutoFake(
        "produto",
        "Produto",
    )

    feed = service(
        produtos=[produto],
        precos={
            "produto": [
                preco(
                    "100.00",
                    "shopee",
                    "x",
                )
            ]
        },
        marketplaces=("shopee",),
    ).gerar(
        conta_id="usr_1",
        limite=999,
        offset=-50,
    )

    assert feed.limite == 50
    assert feed.offset == 0


def test_documentacao_preserva_fronteiras():
    doc = DOC.read_text(encoding="utf-8")

    assert "GET /api/v1/me/feed" in doc

    assert "Esta fase deliberadamente n\u00e3o:" in doc

    assert "- adiciona rota HTTP;" in doc

    assert "- altera o Public App;" in doc

    assert "- envia push;" in doc
