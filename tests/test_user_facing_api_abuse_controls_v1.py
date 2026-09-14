from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from repositories.user_identity_repository import UserIdentityRepository
from services.api_aplicacao.servidor import ServidorApiAplicacao
from services.api_aplicacao.user_facing_abuse_controls import (
    UserFacingAbuseControls,
)
from services.user_identity_service import UserIdentityService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "user_facing_api_abuse_controls_v1.json"


class Clock:
    def __init__(self) -> None:
        self.valor = 1000.0

    def __call__(self) -> float:
        return self.valor

    def avancar(self, segundos: float) -> None:
        self.valor += segundos


def _post(
    url: str,
    payload: dict[str, object],
    *,
    infra: str | None = None,
) -> tuple[int, dict[str, object], dict[str, str]]:
    headers = {
        "Content-Type": "application/json",
    }
    if infra is not None:
        headers["Authorization"] = f"Bearer {infra}"

    request = Request(
        url,
        method="POST",
        headers=headers,
        data=json.dumps(payload).encode("utf-8"),
    )

    try:
        with urlopen(request, timeout=10) as resposta:
            return (
                resposta.status,
                json.loads(resposta.read().decode("utf-8")),
                dict(resposta.headers.items()),
            )
    except HTTPError as erro:
        return (
            erro.code,
            json.loads(erro.read().decode("utf-8")),
            dict(erro.headers.items()),
        )


def _servidor(
    tmp_path: Path,
    limiter: UserFacingAbuseControls,
    *,
    infra_token: str = "",
):
    identity = UserIdentityService(UserIdentityRepository(tmp_path / "identity.sqlite3"))

    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token=infra_token,
        user_identity_service=identity,
        user_facing_abuse_controls=limiter,
    )
    servidor.iniciar()

    endereco = servidor.endereco
    assert endereco is not None
    _, porta = endereco

    return (
        servidor,
        identity,
        f"http://127.0.0.1:{porta}",
    )


def test_contract_define_abuse_controls():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["schema"] == ("projeto-renda-automatica.user-facing-api-abuse-controls")
    assert data["abuse_controls_version"] == 1
    assert data["http"]["limited_status"] == 429
    assert data["http"]["retry_after_header"] is True
    assert data["algorithm"]["thread_safe"] is True
    assert data["algorithm"]["distributed"] is False


def test_register_limite_exato_e_reset_de_janela():
    clock = Clock()
    limiter = UserFacingAbuseControls(
        register_limit=2,
        register_window_seconds=60,
        login_client_limit=100,
        login_subject_limit=100,
        login_window_seconds=60,
        clock=clock,
    )

    assert limiter.avaliar_register("127.0.0.1").permitido is True
    assert limiter.avaliar_register("127.0.0.1").permitido is True

    bloqueado = limiter.avaliar_register("127.0.0.1")
    assert bloqueado.permitido is False
    assert bloqueado.retry_after_seconds == 60

    clock.avancar(60)

    assert limiter.avaliar_register("127.0.0.1").permitido is True


def test_login_subject_limita_mesmo_com_budget_de_cliente():
    clock = Clock()
    limiter = UserFacingAbuseControls(
        register_limit=100,
        register_window_seconds=60,
        login_client_limit=100,
        login_subject_limit=2,
        login_window_seconds=60,
        clock=clock,
    )

    assert (
        limiter.avaliar_login(
            "cliente-a",
            subject=" Alvo@Example.com ",
        ).permitido
        is True
    )
    assert (
        limiter.avaliar_login(
            "cliente-b",
            subject="alvo@example.com",
        ).permitido
        is True
    )

    bloqueado = limiter.avaliar_login(
        "cliente-c",
        subject="ALVO@example.com",
    )
    assert bloqueado.permitido is False


def test_limiter_e_thread_safe():
    limiter = UserFacingAbuseControls(
        register_limit=5,
        register_window_seconds=60,
        login_client_limit=100,
        login_subject_limit=100,
        login_window_seconds=60,
    )

    def tentar() -> bool:
        return limiter.avaliar_register("cliente-concorrente").permitido

    with ThreadPoolExecutor(max_workers=20) as executor:
        resultados = list(
            executor.map(
                lambda _: tentar(),
                range(20),
            )
        )

    assert sum(resultados) == 5


def test_http_register_retorna_429_e_retry_after(tmp_path: Path):
    limiter = UserFacingAbuseControls(
        register_limit=1,
        register_window_seconds=60,
        login_client_limit=100,
        login_subject_limit=100,
        login_window_seconds=60,
    )

    servidor, _, base = _servidor(
        tmp_path,
        limiter,
    )

    try:
        status, _, _ = _post(
            f"{base}/api/v1/auth/register",
            {
                "email": "primeiro@example.com",
                "senha": "uma-senha-forte-123",
            },
        )
        assert status == 201

        status, body, headers = _post(
            f"{base}/api/v1/auth/register",
            {
                "email": "segundo@example.com",
                "senha": "uma-senha-forte-123",
            },
        )

        assert status == 429
        assert body["erro"]["codigo"] == ("limite_requisicoes_excedido")
        assert int(headers["Retry-After"]) >= 1
    finally:
        servidor.encerrar()


def test_http_login_retorna_429_antes_de_nova_autenticacao(
    tmp_path: Path,
):
    limiter = UserFacingAbuseControls(
        register_limit=100,
        register_window_seconds=60,
        login_client_limit=1,
        login_subject_limit=100,
        login_window_seconds=60,
    )

    servidor, identity, base = _servidor(
        tmp_path,
        limiter,
    )
    identity.criar_conta(
        email="usuario@example.com",
        senha="senha-correta-123",
    )

    try:
        status, body, _ = _post(
            f"{base}/api/v1/auth/login",
            {
                "email": "usuario@example.com",
                "senha": "senha-errada-123",
            },
        )
        assert status == 401
        assert body["erro"]["codigo"] == "credenciais_invalidas"

        status, body, headers = _post(
            f"{base}/api/v1/auth/login",
            {
                "email": "usuario@example.com",
                "senha": "senha-correta-123",
            },
        )
        assert status == 429
        assert body["erro"]["codigo"] == ("limite_requisicoes_excedido")
        assert int(headers["Retry-After"]) >= 1
    finally:
        servidor.encerrar()


def test_infra_guard_nao_consumo_budget_do_limiter(tmp_path: Path):
    limiter = UserFacingAbuseControls(
        register_limit=1,
        register_window_seconds=60,
        login_client_limit=100,
        login_subject_limit=100,
        login_window_seconds=60,
    )

    servidor, _, base = _servidor(
        tmp_path,
        limiter,
        infra_token="segredo-infra",
    )

    try:
        status, body, _ = _post(
            f"{base}/api/v1/auth/register",
            {
                "email": "bloqueado@example.com",
                "senha": "uma-senha-forte-123",
            },
        )
        assert status == 401
        assert body["erro"]["codigo"] == ("infraestrutura_nao_autorizada")

        status, _, _ = _post(
            f"{base}/api/v1/auth/register",
            {
                "email": "permitido@example.com",
                "senha": "uma-senha-forte-123",
            },
            infra="segredo-infra",
        )
        assert status == 201
    finally:
        servidor.encerrar()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"register_limit": 0},
        {"register_window_seconds": -1},
        {"login_client_limit": True},
        {"login_subject_limit": 0},
        {"login_window_seconds": 0},
        {"max_buckets": 0},
    ],
)
def test_config_invalida_falha(kwargs):
    with pytest.raises((TypeError, ValueError)):
        UserFacingAbuseControls(**kwargs)


def test_from_env_le_configuracao(monkeypatch):
    monkeypatch.setenv("API_USER_REGISTER_RATE_LIMIT", "7")
    monkeypatch.setenv(
        "API_USER_REGISTER_RATE_WINDOW_SECONDS",
        "120",
    )
    monkeypatch.setenv("API_USER_LOGIN_RATE_LIMIT", "11")
    monkeypatch.setenv(
        "API_USER_LOGIN_SUBJECT_RATE_LIMIT",
        "4",
    )
    monkeypatch.setenv(
        "API_USER_LOGIN_RATE_WINDOW_SECONDS",
        "90",
    )

    limiter = UserFacingAbuseControls.from_env()

    assert limiter.register_limit == 7
    assert limiter.register_window_seconds == 120
    assert limiter.login_client_limit == 11
    assert limiter.login_subject_limit == 4
    assert limiter.login_window_seconds == 90
