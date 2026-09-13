import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "client_transport_v1.json"
DOC = ROOT / "docs" / "12-transporte-cliente-tailscale.md"
SCRIPT = ROOT / "scripts" / "client_transport_tailscale.ps1"
README = ROOT / "README.md"


def _contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_contract_transport_v1():
    data = _contract()
    assert data["schema"] == "projeto-renda-automatica.client-transport"
    assert data["transport_version"] == 1
    assert data["name"] == "tailscale_tcp_over_trusted_tunnel"


def test_backend_permanece_loopback():
    api = _contract()["application_api"]
    assert api["backend_host"] == "127.0.0.1"
    assert api["backend_port"] == 8766
    assert api["backend_must_remain_loopback"] is True


def test_endpoint_remoto_por_ipv4_tailscale():
    remote = _contract()["remote_endpoint"]
    assert remote["provider"] == "tailscale"
    assert remote["host_source"] == "tailscale_ipv4"
    assert remote["tcp_port"] == 18767
    assert remote["client_scheme"] == "http"
    assert remote["magicdns_required"] is False


def test_seguranca_do_transporte():
    sec = _contract()["security"]
    assert sec["tailnet_only"] is True
    assert sec["trusted_encrypted_external_transport"] is True
    assert sec["bearer_required_for_data_routes"] is True
    assert sec["tailscale_funnel_allowed"] is False
    assert sec["public_internet_exposure"] is False


def test_admin_fora_do_contrato_cliente():
    boundaries = _contract()["boundaries"]
    assert boundaries["admin_api_port_8765_is_client_transport"] is False
    assert boundaries["admin_control_plane_is_client_api"] is False


def test_app_privado_fora_do_repo():
    assert _contract()["boundaries"]["private_android_app_in_public_repository"] is False


def test_script_encaminha_somente_para_api_cliente():
    fonte = SCRIPT.read_text(encoding="utf-8")
    assert "127.0.0.1:$BackendPort" in fonte
    assert "BackendPort = 8766" in fonte
    assert "PublicPort = 18767" in fonte
    assert "--tcp=$PublicPort" in fonte

    # A palavra "Funnel" pode aparecer apenas em uma linha informativa
    # como FUNNEL_REQUIRED=False. O que deve ser proibido e uso real
    # do recurso/CLI publico do Tailscale Funnel.
    fonte_lower = fonte.lower()
    assert "tailscale funnel" not in fonte_lower
    assert "tailscale.exe funnel" not in fonte_lower
    assert "--funnel" not in fonte_lower

    assert "8765" not in fonte


def test_script_nao_contem_identidade_da_maquina():
    fonte = SCRIPT.read_text(encoding="utf-8")
    proibidos = [
        "100.73.126.112",
        "desktop-t2kln4l",
        "tail308091.ts.net",
        "RadarControle",
    ]
    for termo in proibidos:
        assert termo not in fonte


def test_documentacao_explica_magicdns_nao_obrigatorio():
    texto = DOC.read_text(encoding="utf-8")
    assert "MagicDNS não é requisito" in texto
    assert "Tailscale Funnel" in texto
    assert "127.0.0.1:8766" in texto
    assert "18767" in texto


def test_readme_expoe_bloco26():
    texto = README.read_text(encoding="utf-8")
    assert "<!-- bloco26-client-transport-v1:start -->" in texto
    assert "Client Transport V1 — Tailscale TCP" in texto
    assert "contracts/client_transport_v1.json" in texto
    assert "docs/12-transporte-cliente-tailscale.md" in texto


def test_contrato_nao_contem_ip_ou_hostname_pessoal():
    texto = CONTRACT.read_text(encoding="utf-8")
    for termo in ["100.73.126.112", "desktop-t2kln4l", "tail308091.ts.net"]:
        assert termo not in texto
