# 63.8738, -149.7525

from __future__ import annotations

from services.scout.mercado_livre_catalog_api import (
    ClienteCatalogoMercadoLivre,
    ErroApiMercadoLivre,
)


class RespostaFake:
    def __init__(
        self,
        status_code,
        payload,
    ):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class SessaoFake:
    def __init__(
        self,
        respostas,
    ):
        self.respostas = list(respostas)
        self.chamadas = []

    def request(
        self,
        metodo,
        url,
        timeout,
        **kwargs,
    ):
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


def cliente(
    sessao,
):
    return ClienteCatalogoMercadoLivre(
        client_id="client-id",
        client_secret="client-secret",
        access_token="access-token",
        refresh_token="refresh-token",
        token_expires_at=4_000_000_000,
        session=sessao,
        agora=lambda: 1_700_000_000,
        persistir_tokens=False,
    )


def test_domain_discovery_mapeia_dominios_e_escapa_query():
    sessao = SessaoFake(
        [
            RespostaFake(
                200,
                [
                    {
                        "domain_id": ("MLB-COMPUTER_PROCESSORS"),
                        "domain_name": ("Processadores"),
                        "category_id": "MLB1693",
                        "category_name": ("Processadores"),
                    },
                    {
                        "domain_id": ("MLB-COMPUTER_MOTHERBOARDS"),
                        "domain_name": ("Placas-mãe"),
                        "category_id": "MLB1692",
                        "category_name": ("Placas-Mãe"),
                    },
                ],
            )
        ]
    )

    dominios = cliente(sessao).descobrir_dominios(
        "Processador AMD Ryzen 7",
        limite=2,
    )

    assert len(dominios) == 2

    assert dominios[0].domain_id == "MLB-COMPUTER_PROCESSORS"

    assert dominios[0].category_id == "MLB1693"

    chamada = sessao.chamadas[0]

    assert chamada["metodo"] == "GET"

    assert "/sites/MLB/domain_discovery/search?" in chamada["url"]

    assert "q=Processador+AMD+Ryzen+7" in chamada["url"]

    assert "limit=2" in chamada["url"]


def test_products_search_aplica_domain_id():
    sessao = SessaoFake(
        [
            RespostaFake(
                200,
                {
                    "results": [
                        {
                            "id": "MLB70617506",
                            "name": ("Placa de vídeo " "NVIDIA RTX 5060"),
                            "domain_id": ("MLB-GRAPHICS_CARDS"),
                            "status": "active",
                        },
                        {
                            "id": "MLB70000000",
                            "name": ("RTX 5060 modelo B"),
                            "domain_id": ("MLB-GRAPHICS_CARDS"),
                            "status": "active",
                        },
                    ]
                },
            )
        ]
    )

    produtos = cliente(sessao).buscar_produtos(
        "Placa de vídeo NVIDIA RTX 5060",
        domain_id="MLB-GRAPHICS_CARDS",
        limite=2,
    )

    assert [produto.product_id for produto in produtos] == [
        "MLB70617506",
        "MLB70000000",
    ]

    assert all(produto.domain_id == "MLB-GRAPHICS_CARDS" for produto in produtos)

    chamada = sessao.chamadas[0]

    assert "/products/search?" in chamada["url"]
    assert "status=active" in chamada["url"]
    assert "site_id=MLB" in chamada["url"]
    assert "limit=2" in chamada["url"]

    assert "domain_id=MLB-GRAPHICS_CARDS" in chamada["url"]


def test_products_search_propaga_429_como_transitorio():
    sessao = SessaoFake(
        [
            RespostaFake(
                429,
                {"message": ("local_rate_limited")},
            )
        ]
    )

    try:
        cliente(sessao).buscar_produtos(
            "SSD NVMe",
            domain_id=("MLB-HARD_DRIVES_AND_SSDS"),
            limite=1,
        )

    except ErroApiMercadoLivre as erro:
        assert erro.status_code == 429
        assert erro.transitorio is True

        assert erro.motivo == "api_mercado_livre_rate_limit"

    else:
        raise AssertionError("Era esperado ErroApiMercadoLivre.")


def test_buscas_rejeitam_consulta_vazia_sem_rede():
    sessao = SessaoFake([])

    api = cliente(sessao)

    for funcao in (
        api.descobrir_dominios,
        api.buscar_produtos,
    ):
        try:
            funcao("   ")

        except ValueError:
            pass

        else:
            raise AssertionError("Consulta vazia deveria falhar.")

    assert sessao.chamadas == []
