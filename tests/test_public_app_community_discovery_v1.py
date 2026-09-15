from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "apps" / "public-mobile"
CLIENT = APP / "src" / "api" / "public-api-client.ts"
SCREEN = APP / "app" / "discover.tsx"
LAYOUT = APP / "app" / "_layout.tsx"
HOME = APP / "app" / "home.tsx"
QUERIES = APP / "src" / "discoveries" / "discovery-queries.ts"
DOC = ROOT / "docs" / "39-community-discovery-v1.md"


def test_app_expoe_descoberta_comunitaria_real():
    client = CLIENT.read_text(encoding="utf-8")
    screen = SCREEN.read_text(encoding="utf-8")
    layout = LAYOUT.read_text(encoding="utf-8")
    home = HOME.read_text(encoding="utf-8")
    queries = QUERIES.read_text(encoding="utf-8")

    assert 'path: "/me/discoveries"' in client
    assert 'method: "POST"' in client
    assert "requiresUserSession: true" in client

    assert 'name="discover"' in layout
    assert 'router.push("/discover" as never)' in home
    assert "Encontrou uma oferta?" in home

    assert "useCommunityDiscoveries" in screen
    assert "useCreateCommunityDiscovery" in screen
    assert "Enviar para análise" in screen
    assert "não publica nada automaticamente" in screen

    assert "api.listCommunityDiscoveries()" in queries
    assert "api.createCommunityDiscovery({ url })" in queries


def test_app_nao_faz_fetch_direto_para_link_contribuido():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            SCREEN,
            QUERIES,
        )
    )

    assert re.search(r"\bfetch\s*\(", source) is None
    assert "Linking.openURL" not in source
    assert "axios" not in source


def test_documentacao_mantem_processamento_posterior_explicito():
    doc = DOC.read_text(encoding="utf-8")

    assert "intake real" in doc
    assert "**não** deve ser gravada diretamente no Catálogo Canônico" in doc
    assert "processador de descoberta comunitária" in doc
    assert "não realiza requisições externas" in doc
