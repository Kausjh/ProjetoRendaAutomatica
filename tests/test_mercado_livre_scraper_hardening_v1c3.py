# 63.8738, -149.7525

from types import SimpleNamespace

from scrapers.mercado_livre_scraper import (
    MercadoLivreScraper,
)
from services.scout.mercado_livre_catalog_api import (
    ErroApiMercadoLivre,
)


class Cliente429UmaVez:
    def __init__(self):
        self.tentativas_busca = 0

    def descobrir_dominios(
        self,
        consulta,
        limite=3,
    ):
        return (
            SimpleNamespace(
                domain_id="MLB-COMPUTER_PROCESSORS",
            ),
        )

    def buscar_produtos(
        self,
        consulta,
        *,
        domain_id=None,
        limite=5,
    ):
        self.tentativas_busca += 1

        if self.tentativas_busca == 1:
            raise ErroApiMercadoLivre(
                "api_mercado_livre_rate_limit",
                status_code=429,
                transitorio=True,
            )

        return ()

    def consultar_snapshot(
        self,
        product_id,
    ):
        raise AssertionError("snapshot nao deveria ser consultado")


class ClienteSemResultados:
    def __init__(self):
        self.dominios = 0
        self.buscas = 0

    def descobrir_dominios(
        self,
        consulta,
        limite=3,
    ):
        self.dominios += 1

        return (
            SimpleNamespace(
                domain_id="MLB-COMPUTER_PROCESSORS",
            ),
        )

    def buscar_produtos(
        self,
        consulta,
        *,
        domain_id=None,
        limite=5,
    ):
        self.buscas += 1
        return ()

    def consultar_snapshot(
        self,
        product_id,
    ):
        raise AssertionError("snapshot nao deveria ser consultado")


def test_rate_limit_padrao_faz_uma_repeticao_com_jitter():
    cliente = Cliente429UmaVez()
    esperas = []

    scraper = MercadoLivreScraper(
        termos_busca=["Ryzen 7"],
        cliente_catalogo=cliente,
        sleep_fn=esperas.append,
        jitter_fn=lambda: 0.25,
    )

    assert scraper.TENTATIVAS_RATE_LIMIT_PADRAO == 1

    assert scraper.buscar_ofertas(limite=1) == []

    assert cliente.tentativas_busca == 2

    assert esperas == [2.25]


def test_orcamento_global_limita_ciclo_sem_resultados():
    cliente = ClienteSemResultados()

    termos = [f"Produto teste {indice}" for indice in range(50)]

    scraper = MercadoLivreScraper(
        termos_busca=termos,
        cliente_catalogo=cliente,
        sleep_fn=lambda _: None,
        jitter_fn=lambda: 0.0,
    )

    assert scraper.buscar_ofertas(limite=1) == []

    # limite=1:
    # 1 * 3 + 8 = 11 unidades de budget.
    # Cada termo sem resultado exige 2 unidades.
    assert cliente.dominios == 5
    assert cliente.buscas == 5


def test_jitter_negativo_e_limitado_a_zero():
    cliente = Cliente429UmaVez()
    esperas = []

    scraper = MercadoLivreScraper(
        termos_busca=["Ryzen 7"],
        cliente_catalogo=cliente,
        sleep_fn=esperas.append,
        jitter_fn=lambda: -10.0,
    )

    scraper.buscar_ofertas(limite=1)

    assert esperas == [2.0]
