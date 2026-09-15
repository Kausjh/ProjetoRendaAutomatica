from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.user_identity_repository import UserIdentityRepository
from services.api_aplicacao.servidor import ServidorApiAplicacao
from services.community_discovery_service import CommunityDiscoveryService
from services.user_identity_service import UserIdentityService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "community_discovery_v1.json"
DOC = ROOT / "docs" / "39-community-discovery-v1.md"
SERVER = ROOT / "services" / "api_aplicacao" / "servidor.py"
SERVICE = ROOT / "services" / "community_discovery_service.py"


def _request(
    url: str,
    *,
    method: str = "GET",
    payload: object | None = None,
    session: str | None = None,
    infra: str | None = None,
) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}

    if session is not None:
        headers["X-User-Session"] = session
    if infra is not None:
        headers["Authorization"] = f"Bearer {infra}"

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )

    try:
        with urlopen(request, timeout=5) as response:
            return (
                response.status,
                json.loads(response.read().decode("utf-8")),
            )
    except HTTPError as error:
        return (
            error.code,
            json.loads(error.read().decode("utf-8")),
        )


@pytest.fixture
def api(tmp_path: Path):
    banco = tmp_path / "user_identity.sqlite3"
    identity = UserIdentityService(UserIdentityRepository(banco))

    conta_a = identity.criar_conta(
        email="a@example.com",
        senha="uma-senha-forte-123",
    )
    conta_b = identity.criar_conta(
        email="b@example.com",
        senha="outra-senha-forte-456",
    )

    sessao_a = identity.emitir_sessao(conta_a)
    sessao_b = identity.emitir_sessao(conta_b)

    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="",
        user_identity_service=identity,
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco

    try:
        yield (
            f"http://127.0.0.1:{porta}",
            banco,
            conta_a,
            conta_b,
            sessao_a.token,
            sessao_b.token,
        )
    finally:
        servidor.encerrar()


def test_cria_e_lista_descoberta_real_por_conta(api):
    base, _, conta_a, _, token_a, _ = api

    status, body = _request(
        f"{base}/api/v1/me/discoveries",
        method="POST",
        payload={
            "url": ("https://www.kabum.com.br/produto/123" "#trecho-que-nao-entra-na-deduplicacao")
        },
        session=token_a,
    )

    assert status == 201
    assert body["dados"]["duplicada"] is False

    item = body["dados"]["item"]
    assert item["status"] == "received"
    assert item["marketplace"] == "kabum"
    assert item["url"].startswith("https://www.kabum.com.br/")
    assert "conta_id" not in item
    assert "url_hash" not in item

    status, body = _request(
        f"{base}/api/v1/me/discoveries",
        session=token_a,
    )

    assert status == 200
    assert body["dados"]["total"] == 1
    assert body["dados"]["itens"][0]["id"] == item["id"]

    with sqlite3.connect(api[1]) as conexao:
        owner = conexao.execute(
            "SELECT conta_id FROM community_discoveries WHERE id = ?",
            (item["id"],),
        ).fetchone()[0]

    assert owner == conta_a.id


def test_mesma_url_da_mesma_conta_e_idempotente(api):
    base, _, _, _, token_a, _ = api
    url = "https://produto.mercadolivre.com.br/MLB-123"

    first_status, first = _request(
        f"{base}/api/v1/me/discoveries",
        method="POST",
        payload={"url": url},
        session=token_a,
    )
    second_status, second = _request(
        f"{base}/api/v1/me/discoveries",
        method="POST",
        payload={"url": url + "#detalhes"},
        session=token_a,
    )

    assert first_status == 201
    assert second_status == 200
    assert second["dados"]["duplicada"] is True
    assert second["dados"]["item"]["id"] == first["dados"]["item"]["id"]


def test_contas_sao_isoladas_e_podem_contribuir_mesma_url(api):
    base, _, _, _, token_a, token_b = api
    url = "https://shopee.com.br/produto-teste"

    status_a, body_a = _request(
        f"{base}/api/v1/me/discoveries",
        method="POST",
        payload={"url": url},
        session=token_a,
    )
    status_b, body_b = _request(
        f"{base}/api/v1/me/discoveries",
        method="POST",
        payload={"url": url},
        session=token_b,
    )

    assert status_a == 201
    assert status_b == 201
    assert body_a["dados"]["item"]["id"] != body_b["dados"]["item"]["id"]

    _, list_a = _request(
        f"{base}/api/v1/me/discoveries",
        session=token_a,
    )
    _, list_b = _request(
        f"{base}/api/v1/me/discoveries",
        session=token_b,
    )

    assert list_a["dados"]["total"] == 1
    assert list_b["dados"]["total"] == 1
    assert list_a["dados"]["itens"][0]["id"] != list_b["dados"]["itens"][0]["id"]


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://localhost/oferta",
        "http://127.0.0.1/oferta",
        "http://192.168.1.10/oferta",
        "https://usuario:senha@example.com/oferta",
    ],
)
def test_links_inseguros_sao_rejeitados(api, url: str):
    base, _, _, _, token_a, _ = api

    status, body = _request(
        f"{base}/api/v1/me/discoveries",
        method="POST",
        payload={"url": url},
        session=token_a,
    )

    assert status == 400
    assert body["erro"]["codigo"] == "descoberta_invalida"


def test_cliente_nao_controla_autoria_nem_status(api):
    base, _, _, _, token_a, _ = api

    status, body = _request(
        f"{base}/api/v1/me/discoveries",
        method="POST",
        payload={
            "url": "https://www.amazon.com.br/dp/ABC123",
            "status": "approved",
            "conta_id": "usr_forjado",
        },
        session=token_a,
    )

    assert status == 400
    assert body["erro"]["codigo"] == "payload_descoberta_invalido"


def test_sessao_e_obrigatoria(api):
    base, *_ = api

    status, body = _request(
        f"{base}/api/v1/me/discoveries",
        method="POST",
        payload={"url": "https://www.kabum.com.br/produto/123"},
    )

    assert status == 401
    assert body["erro"]["codigo"] == "sessao_usuario_obrigatoria"


def test_token_da_api_e_preservado(tmp_path: Path):
    banco = tmp_path / "identity.sqlite3"
    identity = UserIdentityService(UserIdentityRepository(banco))
    conta = identity.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    sessao = identity.emitir_sessao(conta)

    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="segredo-infra",
        user_identity_service=identity,
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco
    base = f"http://127.0.0.1:{porta}"

    try:
        status, body = _request(
            f"{base}/api/v1/me/discoveries",
            session=sessao.token,
        )
        assert status == 401
        assert body["erro"]["codigo"] == "infraestrutura_nao_autorizada"

        status, body = _request(
            f"{base}/api/v1/me/discoveries",
            method="POST",
            payload={"url": "https://www.kabum.com.br/produto/123"},
            session=sessao.token,
            infra="segredo-infra",
        )
        assert status == 201
        assert body["dados"]["item"]["status"] == "received"
    finally:
        servidor.encerrar()


def test_limite_por_hora_e_aplicado_sem_bloquear_idempotencia(tmp_path: Path):
    banco = tmp_path / "identity.sqlite3"
    identity = UserIdentityService(UserIdentityRepository(banco))
    conta = identity.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    sessao = identity.emitir_sessao(conta)

    service = CommunityDiscoveryService(
        CommunityDiscoveryRepository(banco),
        limite_por_hora=1,
    )
    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="",
        user_identity_service=identity,
        community_discovery_service=service,
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco
    base = f"http://127.0.0.1:{porta}"

    try:
        status, _ = _request(
            f"{base}/api/v1/me/discoveries",
            method="POST",
            payload={"url": "https://example.com/oferta-a"},
            session=sessao.token,
        )
        assert status == 201

        status, body = _request(
            f"{base}/api/v1/me/discoveries",
            method="POST",
            payload={"url": "https://example.com/oferta-b"},
            session=sessao.token,
        )
        assert status == 429
        assert body["erro"]["codigo"] == "limite_descobertas_excedido"

        status, body = _request(
            f"{base}/api/v1/me/discoveries",
            method="POST",
            payload={"url": "https://example.com/oferta-a#repetida"},
            session=sessao.token,
        )
        assert status == 200
        assert body["dados"]["duplicada"] is True
    finally:
        servidor.encerrar()


def test_contrato_documenta_fronteira_e_intake_nao_faz_rede():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    doc = DOC.read_text(encoding="utf-8")
    service_source = SERVICE.read_text(encoding="utf-8")
    server_source = SERVER.read_text(encoding="utf-8")

    assert contract["submission"]["account_attribution_server_side"] is True
    assert contract["submission"]["external_network_call_on_intake"] is False
    assert contract["boundaries"]["automatic_catalog_ingestion"] is False
    assert contract["boundaries"]["automatic_publication"] is False

    assert "community_discoveries" in doc
    assert "Catálogo Canônico" in doc
    assert "Price Intelligence" in doc
    assert "/api/v1/me/discoveries" in server_source

    for forbidden in (
        "httpx",
        "requests.get",
        "urllib.request",
        "urlopen(",
    ):
        assert forbidden not in service_source


@pytest.mark.parametrize(
    ("url", "marketplace_esperado"),
    [
        ("https://meli.la/oferta-teste", "mercado_livre"),
        (
            "https://s.click.aliexpress.com/e/_oferta-teste",
            "aliexpress",
        ),
        ("https://amzn.to/oferta-teste", "amazon"),
        ("https://link.amazon/oferta-teste", "amazon"),
    ],
)
def test_marketplaces_de_links_curtos_sao_identificados(
    url: str,
    marketplace_esperado: str,
):
    _, _, marketplace = CommunityDiscoveryService.normalizar_url(url)

    assert marketplace == marketplace_esperado
