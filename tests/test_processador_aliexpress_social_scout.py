# 63.8738, -149.7525

from models.mensagem_social_scout import MensagemSocialScout
from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from services.scout.processador_aliexpress_social_scout import (
    ProcessadorAliExpressSocialScout,
)
from services.validador_preco_aliexpress import (
    ResultadoPrecoAliExpress,
)

ID = "1005001234567890"

URL = "https://pt.aliexpress.com/" f"item/{ID}.html"


class ServiceFake:
    MOTIVO_DESAFIO = "desafio humano/captcha detectado"

    MOTIVO_COOLDOWN = "AliExpress em cooldown apos desafio humano"

    def __init__(
        self,
        resultado=None,
        erro=None,
    ):
        self.resultado = resultado
        self.erro = erro
        self.chamadas = []

    def validar_produtos(self, ids):
        ids = list(ids)
        self.chamadas.append(ids)

        if self.erro:
            raise self.erro

        if self.resultado is None:
            return {}

        return {self.resultado.produto_id: self.resultado}


def mensagem(*links):
    return MensagemSocialScout(
        fonte="telegram",
        chat_id="-1000000000000",
        message_id=77,
        chat_titulo="Teste",
        texto="SSD NVMe 1TB",
        links=tuple(links),
    )


def deteccao(
    preco=299.90,
):
    return ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="SSD NVMe 1TB",
        marketplace="aliexpress",
        preco_oferta=preco,
        motivo="teste",
    )


def valido(
    preco=299.90,
):
    return ResultadoPrecoAliExpress(
        produto_id=ID,
        preco_brl=preco,
        moeda="BRL",
        url_produto=URL,
        valido=True,
        motivo="ok",
        preco_normal_brl=349.90,
        moeda_normal="BRL",
    )


def invalido(motivo):
    return ResultadoPrecoAliExpress(
        produto_id=ID,
        preco_brl=None,
        moeda=None,
        url_produto=URL,
        valido=False,
        motivo=motivo,
    )


def test_link_direto():
    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(),
    )

    r = p.resolver(
        mensagem(URL),
        deteccao(),
    )

    assert r.status == "resolvido"
    assert r.id_produto == ID
    assert r.url_destino == URL


def test_short_link_produto():
    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(),
        resolver_url=lambda _: URL,
    )

    r = p.resolver(
        mensagem("https://s.click.aliexpress.com/e/teste"),
        deteccao(),
    )

    assert r.status == "resolvido"
    assert r.id_produto == ID


def test_coin_rejeitada():
    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(),
        resolver_url=lambda _: ("https://www.aliexpress.com/" "p/coin-index/index.html"),
    )

    r = p.resolver(
        mensagem("https://s.click.aliexpress.com/e/coin"),
        deteccao(),
    )

    assert r.status == "nao_suportado"


def test_404_rejeitado():
    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(),
        resolver_url=lambda _: ("https://www.aliexpress.com/" "s/error/404.html"),
    )

    r = p.resolver(
        mensagem("https://s.click.aliexpress.com/e/404"),
        deteccao(),
    )

    assert r.status == "nao_suportado"


def test_produtos_distintos_sao_ambiguos():
    outro = "https://pt.aliexpress.com/" "item/1005009999999999.html"

    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(),
    )

    r = p.resolver(
        mensagem(
            URL,
            outro,
        ),
        deteccao(),
    )

    assert r.status == "nao_suportado"
    assert r.motivo == "aliexpress_identidade_ambigua"


def test_erro_redirect_e_transitorio():
    def falhar(_):
        raise TimeoutError()

    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(),
        resolver_url=falhar,
    )

    r = p.resolver(
        mensagem(
            URL,
            "https://s.click.aliexpress.com/e/falha",
        ),
        deteccao(),
    )

    assert r.status == "erro"


def test_preco_confirmado():
    service = ServiceFake(valido())

    p = ProcessadorAliExpressSocialScout(
        service=service,
    )

    r = p.resolver(
        mensagem(URL),
        deteccao(),
    )

    v = p.validar(
        deteccao(),
        r,
    )

    assert v.status == "validado"
    assert v.preco_oficial == 299.90
    assert v.preco_original_oficial == 349.90
    assert v.preco_base_confere is True
    assert v.cupom_validado is False
    assert service.chamadas == [[ID]]


def test_preco_divergente():
    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(valido(310.00)),
    )

    r = p.resolver(
        mensagem(URL),
        deteccao(),
    )

    v = p.validar(
        deteccao(),
        r,
    )

    assert v.status == "rejeitado"
    assert v.preco_base_confere is False


def test_sem_preco_grupo():
    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(valido()),
    )

    r = p.resolver(
        mensagem(URL),
        deteccao(),
    )

    v = p.validar(
        deteccao(None),
        r,
    )

    assert v.status == "nao_verificavel"


def test_indisponibilidade_deterministica():
    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(invalido("item indisponivel no pais/regiao")),
    )

    r = p.resolver(
        mensagem(URL),
        deteccao(),
    )

    v = p.validar(
        deteccao(),
        r,
    )

    assert v.status == "nao_verificavel"


def test_desafio_e_transitorio():
    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(invalido(ServiceFake.MOTIVO_DESAFIO)),
    )

    r = p.resolver(
        mensagem(URL),
        deteccao(),
    )

    v = p.validar(
        deteccao(),
        r,
    )

    assert v.status == "erro"


def test_cooldown_e_transitorio():
    p = ProcessadorAliExpressSocialScout(
        service=ServiceFake(invalido(ServiceFake.MOTIVO_COOLDOWN)),
    )

    r = p.resolver(
        mensagem(URL),
        deteccao(),
    )

    v = p.validar(
        deteccao(),
        r,
    )

    assert v.status == "erro"
