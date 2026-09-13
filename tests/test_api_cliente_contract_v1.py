from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from clients.reference_api_v1 import (
    ClienteApiAplicacaoV1,
    ErroApiAplicacao,
)


def _contrato() -> dict:
    return json.loads(Path("contracts/api_v1.contract.json").read_text(encoding="utf-8"))


def test_contrato_v1_e_exclusivamente_read_only():
    contrato = _contrato()

    assert contrato["contract_version"] == 1
    assert contrato["api_version"] == "v1"
    assert contrato["base_path"] == "/api/v1"

    endpoints = contrato["endpoints"]
    assert len(endpoints) == 5
    assert {item["method"] for item in endpoints} == {"GET"}

    assert contrato["mutating_methods"] == {
        "POST": 405,
        "PUT": 405,
        "PATCH": 405,
        "DELETE": 405,
    }


def test_contrato_preserva_fronteira_do_app_privado():
    boundary = _contrato()["repo_boundary"]

    assert boundary["private_android_app_in_public_repo"] is False
    assert boundary["reference_client_public"] is True


def test_contrato_documenta_seguranca_de_rede():
    transport = _contrato()["transport"]

    assert transport["default_host"] == "127.0.0.1"
    assert transport["default_port"] == 8766
    assert transport["remote_bind_requires_bearer_token"] is True


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/v1/health":
            self._json(
                200,
                {"status": "ok", "api_version": "v1"},
            )
            return

        if self.path.startswith("/api/v1/produtos?"):
            self._json(
                200,
                {
                    "api_version": "v1",
                    "total": 1,
                    "limite": 5,
                    "offset": 0,
                    "itens": [{"chave_canonica": "rtx_5070"}],
                },
            )
            return

        if self.path == "/api/v1/produtos/rtx_5070":
            self._json(
                200,
                {
                    "api_version": "v1",
                    "produto": {
                        "chave_canonica": "rtx_5070",
                    },
                    "price_intelligence": None,
                    "precos_atuais": [],
                    "alert_engine": None,
                },
            )
            return

        if self.path.startswith("/api/v1/produtos/rtx_5070/historico?"):
            self._json(
                200,
                {
                    "api_version": "v1",
                    "chave_canonica": "rtx_5070",
                    "limite": 5,
                    "offset": 0,
                    "itens": [],
                },
            )
            return

        if self.path.startswith("/api/v1/alertas?"):
            self._json(
                200,
                {
                    "api_version": "v1",
                    "total": 0,
                    "limite": 5,
                    "offset": 0,
                    "itens": [],
                },
            )
            return

        self._json(
            404,
            {"erro": "Produto nao encontrado."},
        )

    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


@pytest.fixture
def fake_api():
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        _Handler,
    )
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
    )
    thread.start()

    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_cliente_referencia_cobre_contrato_v1(fake_api):
    cliente = ClienteApiAplicacaoV1(
        fake_api,
        timeout=2,
    )

    assert cliente.health()["status"] == "ok"
    assert (
        cliente.listar_produtos(
            limite=5,
            offset=0,
        )["total"]
        == 1
    )
    assert cliente.obter_produto("rtx_5070")["produto"]["chave_canonica"] == "rtx_5070"
    assert (
        cliente.listar_historico(
            "rtx_5070",
            limite=5,
            offset=0,
        )["chave_canonica"]
        == "rtx_5070"
    )
    assert (
        cliente.listar_alertas(
            limite=5,
            offset=0,
        )["total"]
        == 0
    )


def test_cliente_referencia_normaliza_404(fake_api):
    cliente = ClienteApiAplicacaoV1(
        fake_api,
        timeout=2,
    )

    with pytest.raises(
        ErroApiAplicacao,
        match="HTTP 404",
    ) as erro:
        cliente.obter_produto("nao_existe")

    assert erro.value.status == 404
    assert erro.value.mensagem == "Produto nao encontrado."


def test_cliente_referencia_so_expoe_operacoes_get():
    publicos = {nome for nome in dir(ClienteApiAplicacaoV1) if not nome.startswith("_")}

    assert {
        "health",
        "listar_produtos",
        "obter_produto",
        "listar_historico",
        "listar_alertas",
    } <= publicos

    assert (
        not {
            "post",
            "put",
            "patch",
            "delete",
            "publicar",
            "enviar",
        }
        & publicos
    )
