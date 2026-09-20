from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"

CLIENT = APP / "src" / "api" / "public-api-client.ts"

ACCOUNT = APP / "app" / "account.tsx"

MODULE = APP / "src" / "gamification"

PANEL = MODULE / "gamification-panel.tsx"

PRESENTER = MODULE / "gamification-presenter.ts"

QUERIES = MODULE / "gamification-queries.ts"

TYPES = MODULE / "gamification-types.ts"

INDEX = MODULE / "index.ts"

CONTRACT = ROOT / "contracts" / "public_app_gamification_surface_v1.json"

DOC = ROOT / "docs" / "53-public-app-gamification-surface-v1.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_gamification_files_exist():
    for path in (
        PANEL,
        PRESENTER,
        QUERIES,
        TYPES,
        INDEX,
        ACCOUNT,
        CLIENT,
        CONTRACT,
        DOC,
    ):
        assert path.exists(), path


def test_client_expoe_get_gamification():
    source = read(CLIENT)

    assert "getGamification<T = unknown>()" in source

    assert 'path: "/me/gamification"' in source

    start = source.index("getGamification<T = unknown>()")

    end = source.index("getPreferences<T = unknown>()")

    method = source[start:end]

    assert "requiresUserSession: true" in method

    assert 'responseMode: "user-facing-envelope"' in method


def test_presenter_mapeia_backend():
    source = read(PRESENTER)

    fields = (
        "xp_total",
        "nivel",
        "reputacao_total",
        "eventos_total",
        "xp_inicio_nivel",
        "xp_proximo_nivel",
        "xp_no_nivel",
        "xp_necessario_no_nivel",
        "xp_faltante",
        "percentual",
        "nivel_maximo",
        "conquistas",
        "badges_desbloqueadas",
        "ruleset_version",
    )

    for field in fields:
        assert field in source

    assert "calcular_nivel" not in source

    assert "threshold" not in source.lower()


def test_query_usa_api_gamification():
    source = read(QUERIES)

    assert '["gamification", "me"]' in source

    assert "await api.getGamification()" in source

    assert "presentGamification(" in source

    assert "enabled," in source


def test_panel_exibe_estado_principal():
    source = read(PANEL)

    expected = (
        "useGamification(",
        "data.profile.level",
        "data.profile.xpTotal",
        "data.levelProgress.xpRemaining",
        "data.levelProgress.percent",
        "data.profile.reputationTotal",
        "data.unlockedBadges.length",
        "data.achievements.map",
        "achievement.currentProgress",
        "achievement.targetProgress",
        "gamification.refetch()",
    )

    for value in expected:
        assert value in source


def test_account_incorpora_painel():
    source = read(ACCOUNT)

    assert "import { GamificationPanel } " 'from "@/src/gamification";' in source

    assert "<GamificationPanel " "enabled={authenticated} />" in source

    layout = read(APP / "app" / "_layout.tsx")

    assert 'name="gamification"' not in layout


def test_ui_nao_conhece_segredos():
    combined = "\n".join(
        (
            read(PANEL),
            read(ACCOUNT),
            read(QUERIES),
        )
    )

    forbidden = (
        "X-User-Session",
        "Authorization",
        "Bearer ",
        "API_APLICACAO_TOKEN",
        "infrastructureToken",
        "conta_id",
    )

    for value in forbidden:
        assert value not in combined


def test_contract_read_only():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["public_app_gamification_surface_version"] == 1

    assert data["backend"]["path"] == "/api/v1/me/gamification"

    assert data["backend"]["requires_user_session"] is True

    assert data["backend"]["writes_state"] is False

    assert data["architecture"]["dedicated_route"] is False

    assert data["architecture"]["bottom_nav_entry"] is False

    assert data["source_of_truth"]["client_recalculates_progress"] is False

    boundaries = data["boundaries"]

    assert boundaries["xp_write"] is False

    assert boundaries["reputation_write"] is False

    assert boundaries["event_write"] is False

    assert boundaries["missions"] is False

    assert boundaries["community_reputation"] is False

    assert boundaries["offer_scoring_change"] is False


def test_doc_define_smoke_real():
    source = read(DOC)

    assert "GET /api/v1/me/gamification" in source

    assert "tela Conta" in source

    assert "smoke no dispositivo Android real" in source
