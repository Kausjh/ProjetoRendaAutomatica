from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "apps/public-mobile/src/api/public-api-client.ts"
FEED_TYPES = ROOT / "apps/public-mobile/src/feed/feed-types.ts"
FEED_PRESENTER = ROOT / "apps/public-mobile/src/feed/feed-presenter.ts"
FEED_QUERIES = ROOT / "apps/public-mobile/src/feed/feed-queries.ts"
FEED_INDEX = ROOT / "apps/public-mobile/src/feed/index.ts"

CONTRACT = ROOT / "contracts/public_app_personalized_feed_v1.json"
DOC = ROOT / "docs/46-public-app-personalized-feed-v1.md"


def test_contract_define_data_layer_sem_home():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["public_app_personalized_feed_version"] == 1
    assert data["stage"] == "data-layer"
    assert data["backend_route"] == "GET /api/v1/me/feed"
    assert data["transport"]["requires_user_session"] is True
    assert data["boundaries"]["home_surface_changed"] is False
    assert data["boundaries"]["backend_changed"] is False


def test_client_expoe_feed_autenticado():
    source = CLIENT.read_text(encoding="utf-8")
    assert "getPersonalizedFeed" in source
    assert 'path: "/me/feed"' in source
    assert "query: pagination" in source
    assert "requiresUserSession: true" in source
    assert 'responseMode: "user-facing-envelope"' in source


def test_feed_types_preservam_sinais_backend():
    source = FEED_TYPES.read_text(encoding="utf-8")
    for field in (
        "canonicalKey",
        "relevanceScore",
        "reasons",
        "inWatchlist",
        "targetPrice",
        "currentPrice",
        "marketplace",
        "productUrl",
    ):
        assert field in source


def test_presenter_mapeia_campos_snake_case():
    source = FEED_PRESENTER.read_text(encoding="utf-8")
    for field in (
        "canonical_key",
        "nome_canonico",
        "score_relevancia",
        "motivos",
        "em_watchlist",
        "preco_alvo",
        "preco_atual",
        "atualizado_em",
    ):
        assert field in source
    assert "Na sua watchlist" in source
    assert "Preco-alvo atingido" in source
    assert "Marketplace preferido" in source


def test_query_feed_e_auth_aware():
    source = FEED_QUERIES.read_text(encoding="utf-8")
    assert "usePersonalizedFeed" in source
    assert "personalizedFeedQueryKeys" in source
    assert "getPersonalizedFeed" in source
    assert "enabled" in source


def test_feed_index_exporta_camadas():
    source = FEED_INDEX.read_text(encoding="utf-8")
    assert "feed-presenter" in source
    assert "feed-queries" in source
    assert "feed-types" in source


def test_contrato_preserva_fronteira_historica_da_5c1():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "data-layer"
    assert data["boundaries"]["home_surface_changed"] is False


def test_documentacao_define_proximo_passo():
    source = DOC.read_text(encoding="utf-8")
    assert "GET /api/v1/me/feed" in source
    assert "Fase 5C2" in source
    assert "nao substitui visualmente a Home" in source
