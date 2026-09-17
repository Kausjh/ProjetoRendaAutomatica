# 63.8738, -149.7525

from __future__ import annotations

from services.scout.mercado_livre_catalog_api import (
    ClienteCatalogoMercadoLivre,
    ErroApiMercadoLivre,
)


class RespostaFake:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class SessaoFake:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def request(self, metodo, url, timeout, **kwargs):
        self.chamadas.append(
            {
                "metodo": metodo,
                "url": url,
                "timeout": timeout,
                "kwargs": kwargs,
            }
        )

        if not self.respostas:
            raise AssertionError("Resposta fake ausente.")

        return self.respostas.pop(0)


def cliente(session, **kwargs):
    return ClienteCatalogoMercadoLivre(
        client_id="client-id",
        client_secret="client-secret",
        access_token="access-token",
        refresh_token="refresh-token",
        token_expires_at=4_000_000_000,
        session=session,
        agora=lambda: 1_700_000_000,
        persistir_tokens=False,
        **kwargs,
    )


def test_catalogo_escolhe_menor_preco_brl_com_desempate_estavel():
    session = SessaoFake(
        [
            RespostaFake(
                200,
                {
                    "id": "MLB75627492",
                    "name": "Soprador Mini Turbo",
                },
            ),
            RespostaFake(
                200,
                {
                    "results": [
                        {
                            "item_id": "MLB900",
                            "price": 49.90,
                            "currency_id": "BRL",
                            "seller_id": 1,
                        },
                        {
                            "item_id": "MLB800",
                            "price": 43.99,
                            "currency_id": "BRL",
                            "seller_id": 2,
                        },
                        {
                            "item_id": "MLB700",
                            "price": 43.99,
                            "currency_id": "BRL",
                            "seller_id": 3,
                        },
                        {
                            "item_id": "MLB600",
                            "price": 1.00,
                            "currency_id": "USD",
                            "seller_id": 4,
                        },
                    ]
                },
            ),
        ]
    )

    snapshot = cliente(session).consultar_snapshot("MLB75627492")

    assert snapshot is not None
    assert snapshot.product_id == "MLB75627492"
    assert snapshot.item_id == "MLB700"
    assert snapshot.preco == 43.99
    assert snapshot.currency_id == "BRL"
    assert snapshot.titulo == "Soprador Mini Turbo"


def test_catalogo_descarta_preco_invalido_e_quantidade_zero():
    session = SessaoFake(
        [
            RespostaFake(
                200,
                {
                    "id": "MLB75627492",
                    "name": "Produto",
                },
            ),
            RespostaFake(
                200,
                {
                    "results": [
                        {
                            "item_id": "MLB1",
                            "price": 0,
                            "currency_id": "BRL",
                        },
                        {
                            "item_id": "MLB2",
                            "price": 10,
                            "currency_id": "BRL",
                            "available_quantity": 0,
                        },
                    ]
                },
            ),
        ]
    )

    snapshot = cliente(session).consultar_snapshot("MLB75627492")

    assert snapshot is None


def test_401_renova_token_uma_vez_e_repete_request():
    session = SessaoFake(
        [
            RespostaFake(
                401,
                {
                    "message": "unauthorized",
                },
            ),
            RespostaFake(
                200,
                {
                    "access_token": "novo-access",
                    "refresh_token": "novo-refresh",
                    "expires_in": 21600,
                },
            ),
            RespostaFake(
                200,
                {
                    "id": "MLB75627492",
                    "name": "Produto",
                },
            ),
            RespostaFake(
                200,
                {
                    "results": [
                        {
                            "item_id": "MLB1",
                            "price": 43.99,
                            "currency_id": "BRL",
                        },
                    ]
                },
            ),
        ]
    )

    snapshot = cliente(session).consultar_snapshot("MLB75627492")

    assert snapshot is not None

    assert session.chamadas[1]["metodo"] == "POST"
    assert session.chamadas[1]["url"].endswith("/oauth/token")

    headers_repeticao = session.chamadas[2]["kwargs"]["headers"]

    assert headers_repeticao["Authorization"] == "Bearer novo-access"


def test_429_e_classificado_como_transitorio():
    session = SessaoFake(
        [
            RespostaFake(
                429,
                {
                    "message": "too many requests",
                },
            ),
        ]
    )

    try:
        cliente(session).consultar_snapshot("MLB75627492")
    except ErroApiMercadoLivre as erro:
        assert erro.status_code == 429
        assert erro.transitorio is True
        assert erro.motivo == "api_mercado_livre_rate_limit"
    else:
        raise AssertionError("Era esperado ErroApiMercadoLivre.")


def test_product_id_invalido_nao_faz_rede():
    session = SessaoFake([])

    try:
        cliente(session).consultar_snapshot("123")
    except ErroApiMercadoLivre as erro:
        assert erro.motivo == "mercado_livre_product_id_invalido"
        assert erro.transitorio is False
    else:
        raise AssertionError("Era esperado ErroApiMercadoLivre.")

    assert session.chamadas == []
