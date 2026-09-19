from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from models.personalized_feed import ItemFeedPersonalizado, PaginaFeedPersonalizado
from repositories.user_identity_repository import UserIdentityRepository
from services.api_aplicacao.servidor import ServidorApiAplicacao
from services.user_identity_service import UserIdentityService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "user_facing_api_personalized_feed_v1.json"
RUNTIME = ROOT / "runtime.py"


class FeedFake:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, int]] = []

    def gerar(self, *, conta_id: str, limite: int, offset: int) -> PaginaFeedPersonalizado:
        self.calls.append((conta_id, limite, offset))
        item = ItemFeedPersonalizado(
            canonical_key="produto_" + conta_id,
            nome_canonico="Produto Teste",
            categoria="hardware",
            marca="marca",
            modelo="modelo",
            score_relevancia=140,
            motivos=("watchlist", "preco_alvo_atingido"),
            em_watchlist=True,
            preco_alvo=Decimal("950.00"),
            preco_atual=Decimal("900.00"),
            marketplace="mercado_livre",
            identificador="sku-1",
            link="https://example.test/item",
            atualizado_em="2026-09-19T12:00:00-03:00",
        )
        return PaginaFeedPersonalizado(
            total=1,
            limite=limite,
            offset=offset,
            itens=(item,),
        )


def request_json(url: str, *, session: str | None = None, infra: str | None = None):
    headers: dict[str, str] = {}
    if session is not None:
        headers["X-User-Session"] = session
    if infra is not None:
        headers["Authorization"] = f"Bearer {infra}"
    request = Request(url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def criar_api(tmp_path: Path, *, infra_token: str = ""):
    repo = UserIdentityRepository(tmp_path / "identity.sqlite3")
    identity = UserIdentityService(repo)
    conta_a = identity.criar_conta(email="a@example.com", senha="uma-senha-forte-123")
    conta_b = identity.criar_conta(email="b@example.com", senha="uma-senha-forte-456")
    sessao_a = identity.emitir_sessao(conta_a)
    sessao_b = identity.emitir_sessao(conta_b)
    feed = FeedFake()
    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token=infra_token,
        user_identity_service=identity,
        personalized_feed_service=feed,  # type: ignore[arg-type]
    )
    servidor.iniciar()
    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco
    return servidor, f"http://127.0.0.1:{porta}", conta_a, conta_b, sessao_a, sessao_b, feed


def test_contract_define_get_me_feed():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["personalized_feed_http_version"] == 1
    route = data["route"]
    assert route["method"] == "GET"
    assert route["path"] == "/api/v1/me/feed"
    assert route["requires_user_session"] is True
    assert route["identity_source"] == "X-User-Session"
    assert route["client_account_id_accepted"] is False


def test_feed_exige_sessao(tmp_path: Path):
    servidor, base, _, _, _, _, feed = criar_api(tmp_path)
    try:
        status, body = request_json(f"{base}/api/v1/me/feed")
        assert status == 401
        assert body["erro"]["codigo"] == "sessao_usuario_obrigatoria"
        assert feed.calls == []
    finally:
        servidor.encerrar()


def test_feed_serializa_pagina(tmp_path: Path):
    servidor, base, conta_a, _, sessao_a, _, feed = criar_api(tmp_path)
    try:
        status, body = request_json(
            f"{base}/api/v1/me/feed?limite=10&offset=0",
            session=sessao_a.token,
        )
        assert status == 200
        dados = body["dados"]
        assert dados["total"] == 1
        assert dados["limite"] == 10
        assert dados["offset"] == 0
        item = dados["itens"][0]
        assert item["canonical_key"] == "produto_" + conta_a.id
        assert item["score_relevancia"] == 140
        assert item["motivos"] == ["watchlist", "preco_alvo_atingido"]
        assert item["preco_alvo"] == "950.00"
        assert item["preco_atual"] == "900.00"
        assert feed.calls == [(conta_a.id, 10, 0)]
    finally:
        servidor.encerrar()


def test_conta_id_da_query_nao_override_sessao(tmp_path: Path):
    servidor, base, conta_a, conta_b, sessao_a, _, feed = criar_api(tmp_path)
    try:
        status, body = request_json(
            f"{base}/api/v1/me/feed?conta_id={conta_b.id}",
            session=sessao_a.token,
        )
        assert status == 200
        assert feed.calls[-1][0] == conta_a.id
        assert body["dados"]["itens"][0]["canonical_key"] == "produto_" + conta_a.id
    finally:
        servidor.encerrar()


def test_paginacao_invalida_retorna_400(tmp_path: Path):
    servidor, base, _, _, sessao_a, _, feed = criar_api(tmp_path)
    try:
        status, body = request_json(
            f"{base}/api/v1/me/feed?limite=abc",
            session=sessao_a.token,
        )
        assert status == 400
        assert body["erro"]["codigo"] == "paginacao_invalida"
        assert feed.calls == []
    finally:
        servidor.encerrar()


def test_feed_preserva_bearer_infra(tmp_path: Path):
    servidor, base, _, _, sessao_a, _, feed = criar_api(
        tmp_path,
        infra_token="segredo-infra",
    )
    try:
        sem_infra, body = request_json(
            f"{base}/api/v1/me/feed",
            session=sessao_a.token,
        )
        assert sem_infra == 401
        assert body["erro"]["codigo"] == "infraestrutura_nao_autorizada"
        assert feed.calls == []
        com_infra, body = request_json(
            f"{base}/api/v1/me/feed",
            session=sessao_a.token,
            infra="segredo-infra",
        )
        assert com_infra == 200
        assert body["dados"]["total"] == 1
    finally:
        servidor.encerrar()


def test_feed_indisponivel_retorna_503(tmp_path: Path):
    repo = UserIdentityRepository(tmp_path / "identity.sqlite3")
    identity = UserIdentityService(repo)
    conta = identity.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    sessao = identity.emitir_sessao(conta)
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
        status, body = request_json(
            f"http://127.0.0.1:{porta}/api/v1/me/feed",
            session=sessao.token,
        )
        assert status == 503
        assert body["erro"]["codigo"] == "feed_personalizado_indisponivel"
    finally:
        servidor.encerrar()


def test_runtime_injeta_feed_core():
    source = RUNTIME.read_text(encoding="utf-8")
    assert "PersonalizedFeedService" in source
    assert "catalogo_repository=controlador_api.catalogo_repository" in source
    assert "price_intelligence_repository=" in source
    assert "personalized_feed_service=personalized_feed_service" in source


def test_public_app_ainda_fora_da_fase_5b():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["boundaries"]["public_app_integration"] is False
    assert data["boundaries"]["push_delivery"] is False
