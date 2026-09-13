from __future__ import annotations

import json
from pathlib import Path

import pytest

from clients.reference_api_v1 import ClienteApiAplicacaoV1


def _policy() -> dict:
    return json.loads(Path("contracts/client_access_policy_v1.json").read_text(encoding="utf-8"))


def test_policy_v1_preserva_fronteiras():
    policy = _policy()
    assert policy["policy_version"] == 1
    assert policy["principles"]["api_application_read_only"] is True
    assert policy["principles"]["admin_control_plane_exposed_to_clients"] is False
    assert policy["principles"]["private_android_app_in_public_repo"] is False


def test_loopback_http_continua_permitido_sem_token():
    cliente = ClienteApiAplicacaoV1("http://127.0.0.1:8766")
    assert cliente.base_url == "http://127.0.0.1:8766"
    assert cliente.token == ""


@pytest.mark.parametrize(
    "url",
    [
        "http://192.168.1.50:8766",
        "http://100.64.0.10:8766",
        "http://api.exemplo.invalid:8766",
    ],
)
def test_http_remoto_puro_e_rejeitado_mesmo_com_token(url):
    with pytest.raises(ValueError, match="HTTP remoto exige"):
        ClienteApiAplicacaoV1(url, token="segredo")


def test_https_remoto_exige_token():
    with pytest.raises(
        ValueError,
        match="Acesso remoto exige Bearer token",
    ):
        ClienteApiAplicacaoV1("https://api.exemplo.invalid")


def test_https_remoto_com_token_e_aceito():
    cliente = ClienteApiAplicacaoV1(
        "https://api.exemplo.invalid",
        token="segredo",
    )
    assert cliente.token == "segredo"
    assert cliente.transporte_confiavel is False


def test_http_remoto_em_tunel_confiavel_exige_token():
    with pytest.raises(
        ValueError,
        match="Acesso remoto exige Bearer token",
    ):
        ClienteApiAplicacaoV1(
            "http://100.64.0.10:8766",
            transporte_confiavel=True,
        )


def test_http_remoto_em_tunel_confiavel_com_token_e_aceito():
    cliente = ClienteApiAplicacaoV1(
        "http://100.64.0.10:8766",
        token="segredo",
        transporte_confiavel=True,
    )
    assert cliente.transporte_confiavel is True
    assert cliente.token == "segredo"


@pytest.mark.parametrize(
    "url",
    [
        "ftp://127.0.0.1:8766",
        "http://usuario:senha@127.0.0.1:8766",
        "http://127.0.0.1:8766/api/v1",
        "http://127.0.0.1:8766?x=1",
        "http://127.0.0.1:8766#frag",
    ],
)
def test_base_url_ambigua_ou_insegura_e_rejeitada(url):
    with pytest.raises(ValueError):
        ClienteApiAplicacaoV1(url)


def test_policy_machine_readable_descreve_quatro_modos():
    modes = _policy()["modes"]
    assert set(modes) == {
        "loopback_http",
        "remote_https",
        "remote_http_over_trusted_tunnel",
        "remote_plain_http",
    }
    assert modes["loopback_http"]["allowed"] is True
    assert modes["remote_https"]["allowed"] is True
    assert modes["remote_http_over_trusted_tunnel"]["allowed"] is True
    assert modes["remote_plain_http"]["allowed"] is False


def test_admin_8765_nao_faz_parte_do_contrato_cliente():
    assert "direct_client_access_to_admin_port_8765" in _policy()["forbidden"]
