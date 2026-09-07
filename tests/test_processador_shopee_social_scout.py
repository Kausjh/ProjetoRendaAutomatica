# 63.8738, -149.7525

from models.mensagem_social_scout import MensagemSocialScout
from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from services.scout.processador_shopee_social_scout import (
    ProcessadorShopeeSocialScout,
)


class ShopeeApiFake:
    def __init__(
        self,
        produto=None,
        erro: Exception | None = None,
    ):
        self.produto = produto
        self.erro = erro
        self.chamadas = []

    def buscar_produto_por_id(
        self,
        item_id,
        shop_id=None,
    ):
        self.chamadas.append(
            (
                str(item_id),
                (str(shop_id) if shop_id is not None else None),
            )
        )

        if self.erro is not None:
            raise self.erro

        return self.produto


class RespostaFake:
    def __init__(
        self,
        *,
        url,
        history=None,
        status_ok=True,
    ):
        self.url = url
        self.history = list(history or [])
        self.headers = {}
        self.status_ok = status_ok

    def raise_for_status(self):
        if not self.status_ok:
            import requests

            raise requests.HTTPError("falha simulada")

    def close(self):
        return None


class HopFake:
    def __init__(
        self,
        url,
        location=None,
    ):
        self.url = url
        self.headers = {}

        if location:
            self.headers["Location"] = location


def mensagem(
    link=("https://shopee.com.br/" "product/10/123"),
):
    return MensagemSocialScout(
        fonte="telegram",
        chat_id="-100123",
        message_id=77,
        chat_titulo="Grupo Teste",
        texto="SSD NVMe Kingston 1TB",
        links=(link,),
    )


def deteccao(
    preco=299.90,
    link=("https://shopee.com.br/" "product/10/123"),
):
    return ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="SSD NVMe Kingston 1TB",
        marketplace="shopee",
        preco_oferta=preco,
        links=(link,),
        motivo="teste",
    )


def produto(
    *,
    item_id=123,
    shop_id=10,
    nome="SSD NVMe Kingston 1TB",
    preco_min="299.90",
    preco_max="299.90",
):
    return {
        "itemId": item_id,
        "shopId": shop_id,
        "productName": nome,
        "productLink": ("https://shopee.com.br/" f"product/{shop_id}/{item_id}"),
        "priceMin": preco_min,
        "priceMax": preco_max,
    }


def test_resolve_por_identidade_exata_e_valida():
    api = ShopeeApiFake(produto())

    processador = ProcessadorShopeeSocialScout(service=api)

    resolucao = processador.resolver(
        mensagem(),
        deteccao(),
    )

    assert resolucao.status == "resolvido"
    assert resolucao.id_produto == "123"

    assert api.chamadas == [("123", "10")]

    validacao = processador.validar(
        deteccao(),
        resolucao,
    )

    assert validacao.status == "validado"
    assert validacao.preco_oficial == 299.90


def test_titulo_nao_define_mais_identidade():
    api = ShopeeApiFake(produto(nome=("Nome oficial totalmente " "diferente da mensagem")))

    processador = ProcessadorShopeeSocialScout(service=api)

    resolucao = processador.resolver(
        mensagem(),
        deteccao(),
    )

    assert resolucao.status == "resolvido"

    assert resolucao.motivo == "produto_shopee_identificado_por_id_exato"


def test_resolve_shortlink_pelo_redirect(
    monkeypatch,
):
    short = "https://s.shopee.com.br/teste"

    resposta = RespostaFake(
        url="https://shopee.com.br/login",
        history=[
            HopFake(
                short,
                ("https://shopee.com.br/" "product/10/123"),
            ),
        ],
    )

    monkeypatch.setattr(
        ("services.scout." "processador_shopee_social_scout." "requests.get"),
        lambda *args, **kwargs: resposta,
    )

    api = ShopeeApiFake(produto())

    processador = ProcessadorShopeeSocialScout(service=api)

    resolucao = processador.resolver(
        mensagem(short),
        deteccao(link=short),
    )

    assert resolucao.status == "resolvido"
    assert api.chamadas == [("123", "10")]


def test_shortlink_sem_identidade_nao_chuta_produto(
    monkeypatch,
):
    short = "https://s.shopee.com.br/teste"

    resposta = RespostaFake(
        url="https://shopee.com.br/login",
    )

    monkeypatch.setattr(
        ("services.scout." "processador_shopee_social_scout." "requests.get"),
        lambda *args, **kwargs: resposta,
    )

    api = ShopeeApiFake(produto())

    processador = ProcessadorShopeeSocialScout(service=api)

    resolucao = processador.resolver(
        mensagem(short),
        deteccao(link=short),
    )

    assert resolucao.status == "nao_suportado"

    assert resolucao.motivo == "shopee_identidade_nao_resolvida"

    assert api.chamadas == []


def test_identidade_divergente_da_api_e_bloqueada():
    api = ShopeeApiFake(
        produto(
            item_id=999,
        )
    )

    processador = ProcessadorShopeeSocialScout(service=api)

    resolucao = processador.resolver(
        mensagem(),
        deteccao(),
    )

    assert resolucao.status == "erro"

    assert resolucao.motivo == "api_shopee_retornou_identidade_divergente"


def test_preco_divergente_e_rejeitado():
    api = ShopeeApiFake(produto())

    processador = ProcessadorShopeeSocialScout(service=api)

    resolucao = processador.resolver(
        mensagem(),
        deteccao(preco=250.00),
    )

    validacao = processador.validar(
        deteccao(preco=250.00),
        resolucao,
    )

    assert validacao.status == "rejeitado"

    assert validacao.motivo == "preco_base_shopee_divergente"


def test_variantes_de_preco_nao_sao_confirmadas():
    api = ShopeeApiFake(
        produto(
            preco_min="299.90",
            preco_max="399.90",
        )
    )

    processador = ProcessadorShopeeSocialScout(service=api)

    resolucao = processador.resolver(
        mensagem(),
        deteccao(),
    )

    validacao = processador.validar(
        deteccao(),
        resolucao,
    )

    assert validacao.status == "nao_verificavel"


def test_falha_api_e_transitoria():
    api = ShopeeApiFake(erro=RuntimeError("falha simulada"))

    processador = ProcessadorShopeeSocialScout(service=api)

    resolucao = processador.resolver(
        mensagem(),
        deteccao(),
    )

    assert resolucao.status == "erro"

    assert resolucao.motivo == "falha_api_shopee_resolucao"
