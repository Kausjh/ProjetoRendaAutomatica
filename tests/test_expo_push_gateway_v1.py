from __future__ import annotations

import json

import httpx
import pytest

from models.push_dispatcher import MensagemPushExpo
from services.expo_push_gateway import (
    EXPO_PUSH_RECEIPTS_URL,
    EXPO_PUSH_SEND_URL,
    ErroExpoPush,
    ExpoPushGateway,
)


def _mensagem(
    *,
    dispositivo_id: str = "dev_1",
    token: str = "ExponentPushToken[token-super-secreto-123]",
) -> MensagemPushExpo:
    return MensagemPushExpo(
        dispositivo_id=dispositivo_id,
        push_token=token,
        titulo="Preco caiu",
        corpo="Sua oferta monitorada ficou mais barata.",
        dados={"type": "price_alert", "canonicalKey": "gpu_teste"},
    )


def test_payload_usa_canal_ofertas_e_dados_de_navegacao():
    payload = _mensagem().como_payload()
    assert payload["channelId"] == "ofertas"
    assert payload["priority"] == "high"
    assert payload["data"] == {"type": "price_alert", "canonicalKey": "gpu_teste"}


def test_repr_nao_expoe_push_token():
    assert "token-super-secreto" not in repr(_mensagem())


def test_envio_retorna_tickets_na_mesma_ordem():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == EXPO_PUSH_SEND_URL
        corpo = json.loads(request.content)
        assert len(corpo) == 2
        assert corpo[0]["channelId"] == "ofertas"
        return httpx.Response(
            200,
            json={
                "data": [
                    {"status": "ok", "id": "ticket_1"},
                    {"status": "ok", "id": "ticket_2"},
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    tickets = ExpoPushGateway(client=client).enviar(
        [
            _mensagem(dispositivo_id="dev_1"),
            _mensagem(
                dispositivo_id="dev_2",
                token="ExponentPushToken[outro-token-secreto]",
            ),
        ]
    )

    assert [ticket.ticket_id for ticket in tickets] == ["ticket_1", "ticket_2"]
    assert all(ticket.status == "ok" for ticket in tickets)


def test_ticket_device_not_registered_e_sanitizado():
    token = "ExponentPushToken[token-que-nao-pode-vazar]"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "status": "error",
                        "message": f'"{token}" is not registered',
                        "details": {"error": "DeviceNotRegistered"},
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    ticket = ExpoPushGateway(client=client).enviar([_mensagem(token=token)])[0]

    assert ticket.status == "error"
    assert ticket.erro_codigo == "DeviceNotRegistered"
    assert token not in (ticket.erro_mensagem or "")
    assert "[push-token-redacted]" in (ticket.erro_mensagem or "")


def test_http_429_e_retryable_e_respeita_retry_after():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            headers={"Retry-After": "17"},
            json={"errors": [{"code": "TOO_MANY_REQUESTS"}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    gateway = ExpoPushGateway(client=client)

    with pytest.raises(ErroExpoPush) as capturado:
        gateway.enviar([_mensagem()])

    erro = capturado.value
    assert erro.status_code == 429
    assert erro.retryable is True
    assert erro.retry_after_seconds == 17


def test_receipts_ok_error_e_ausente():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == EXPO_PUSH_RECEIPTS_URL
        assert json.loads(request.content) == {
            "ids": ["ticket_ok", "ticket_error", "ticket_ausente"]
        }
        return httpx.Response(
            200,
            json={
                "data": {
                    "ticket_ok": {"status": "ok"},
                    "ticket_error": {
                        "status": "error",
                        "message": "device dead",
                        "details": {"error": "DeviceNotRegistered"},
                    },
                }
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    recibos = ExpoPushGateway(client=client).obter_recibos(
        ["ticket_ok", "ticket_error", "ticket_ausente"]
    )

    assert recibos["ticket_ok"].status == "ok"
    assert recibos["ticket_error"].status == "error"
    assert recibos["ticket_error"].erro_codigo == "DeviceNotRegistered"
    assert "ticket_ausente" not in recibos


def test_limites_locais_impedem_request_invalida():
    gateway = ExpoPushGateway(
        client=httpx.Client(
            transport=httpx.MockTransport(
                lambda request: pytest.fail("rede nao deveria ser chamada")
            )
        )
    )

    mensagens = [
        _mensagem(
            dispositivo_id=f"dev_{indice}",
            token=f"ExponentPushToken[token-{indice}]",
        )
        for indice in range(101)
    ]

    with pytest.raises(ValueError, match="100 mensagens"):
        gateway.enviar(mensagens)

    with pytest.raises(ValueError, match="1000 receipt"):
        gateway.obter_recibos([f"ticket_{indice}" for indice in range(1001)])


def test_gateway_nao_exige_autenticacao_extra():
    headers_observados: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        headers_observados.update(dict(request.headers))
        return httpx.Response(
            200,
            json={"data": [{"status": "ok", "id": "ticket_1"}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    ExpoPushGateway(client=client).enviar([_mensagem()])
    assert "authorization" not in headers_observados
