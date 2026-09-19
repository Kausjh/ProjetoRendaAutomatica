from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

HOME = ROOT / "apps" / "public-mobile" / "app" / "home.tsx"

CONTRACT = ROOT / "contracts" / "public_app_personalized_feed_home_v1.json"

DOC = ROOT / "docs" / "47-public-app-personalized-feed-home-v1.md"


def test_home_usa_feed_personalizado_real():
    source = HOME.read_text(encoding="utf-8")

    assert "usePersonalizedFeed" in source
    assert "usePersonalizedFeed(50, 0, authenticated)" in source
    assert "useProductList" not in source
    assert "products." not in source


def test_home_exibe_motivos_de_relevancia():
    source = HOME.read_text(encoding="utf-8")

    assert "PersonalizationReasons" in source
    assert "item.reasons.slice(0, 3)" in source
    assert "personalizedFeedReasonLabel(reason)" in source
    assert "sparkles-outline" in source


def test_home_preserva_card_e_detalhe_do_produto():
    source = HOME.read_text(encoding="utf-8")

    assert "feedItemToProductCard" in source
    assert "ProductCardView" in source
    assert 'pathname: "/product/[canonicalKey]"' in source


def test_home_preserva_acoes_rapidas_da_watchlist():
    source = HOME.read_text(encoding="utf-8")

    assert "useWatchlist(authenticated)" in source
    assert "useUpsertWatchlist()" in source
    assert "useDeleteWatchlist()" in source
    assert "toggleWatchlist" in source
    assert "watchedKeys.has(item.canonicalKey)" in source


def test_mutacao_watchlist_recarrega_feed():
    source = HOME.read_text(encoding="utf-8")

    assert source.count("await feed.refetch();") == 2


def test_home_refresh_atualiza_feed_e_watchlist():
    source = HOME.read_text(encoding="utf-8")

    assert "feed.isRefetching || watchlist.isRefetching" in source
    assert "feed.refetch()" in source
    assert "watchlist.refetch()" in source


def test_home_nao_faz_fallback_generico_disfarcado():
    source = HOME.read_text(encoding="utf-8")

    assert "Seu feed ainda está vazio" in source
    assert "useProductList" not in source


def test_contrato_5c2_define_home_personalizada():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["public_app_personalized_feed_home_version"] == 1
    assert data["stage"] == "home-surface"
    assert data["source"]["generic_product_list_as_personalized_fallback"] is False
    assert data["visible_signals"]["reason_chips"] is True
    assert data["preserved_capabilities"]["watchlist_quick_actions"] is True


def test_documentacao_registra_smoke_como_proximo_passo():
    source = DOC.read_text(encoding="utf-8")

    assert "usePersonalizedFeed" in source
    assert "smoke no dispositivo real" in source
