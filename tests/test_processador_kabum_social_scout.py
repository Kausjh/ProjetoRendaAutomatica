# 63.8738, -149.7525

from models.mensagem_social_scout import (
    MensagemSocialScout,
)
from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from services.kabum_preco_cdp_service import (
    ResultadoPrecoKabum,
)
from services.scout.processador_kabum_social_scout import (
    ProcessadorKabumSocialScout,
)

ID = "699153"

URL = "https://www.kabum.com.br/" "produto/699153/monitor-teste"


class ServiceFake:
    def __init__(
        self,
        resultado=None,
        erro=None,
    ):
        self.resultado = resultado
        self.erro = erro
        self.chamadas = []

    def validar(
        self,
        produto_id,
        url_produto,
    ):
        self.chamadas.append(
            (
                produto_id,
                url_produto,
            )
        )

        if self.erro is not None:
            raise self.erro

        return self.resultado


def mensagem(
    *links,
):
    return MensagemSocialScout(
        fonte="telegram",
        chat_id="-1000000000000",
        message_id=77,
        chat_titulo="Teste",
        texto="Monitor Gamer",
        links=tuple(links),
    )


def deteccao(
    *,
    marketplace="kabum",
    preco=649.99,
):
    return ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="Monitor Gamer",
        marketplace=marketplace,
        preco_oferta=preco,
        motivo="teste",
    )


def resultado_valido(
    *,
    preco=649.99,
    disponivel=None,
):
    return ResultadoPrecoKabum(
        produto_id=ID,
        valido=True,
        motivo=("preco_kabum_" "confirmado_jsonld"),
        url_produto=URL,
        titulo="Monitor Gamer Oficial",
        preco_brl=preco,
        disponivel=disponivel,
    )


def test_link_direto_resolve():
    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(),
    )

    resultado = processador.resolver(
        mensagem(URL),
        deteccao(),
    )

    assert resultado.status == "resolvido"
    assert resultado.marketplace == "kabum"
    assert resultado.id_produto == ID


def test_tiddly_prova_kabum():
    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(),
        resolver_url=lambda _: URL,
    )

    resultado = processador.resolver(
        mensagem("https://tidd.ly/teste"),
        deteccao(marketplace=None),
    )

    assert resultado.status == "resolvido"
    assert resultado.marketplace == "kabum"
    assert resultado.id_produto == ID


def test_tiddly_categoria_nao_vira_produto():
    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(),
        resolver_url=lambda _: ("https://www.kabum.com.br/" "hardware"),
    )

    resultado = processador.resolver(
        mensagem("https://tidd.ly/categoria"),
        deteccao(marketplace=None),
    )

    assert resultado.status == "nao_suportado"

    assert resultado.motivo == "kabum_destino_nao_e_produto"


def test_tiddly_outro_host_nao_vira_kabum():
    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(),
        resolver_url=lambda _: ("https://loja-exemplo.com/" "produto/1"),
    )

    resultado = processador.resolver(
        mensagem("https://tidd.ly/outro"),
        deteccao(marketplace=None),
    )

    assert resultado.status == "nao_suportado"


def test_tiddly_destino_misto_bloqueia():
    destinos = {
        "https://tidd.ly/kabum": URL,
        "https://tidd.ly/outro": ("https://loja-exemplo.com/" "produto/1"),
    }

    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(),
        resolver_url=lambda url: (destinos[url]),
    )

    resultado = processador.resolver(
        mensagem(*destinos.keys()),
        deteccao(marketplace=None),
    )

    assert resultado.status == "nao_suportado"

    assert resultado.motivo == "tiddly_destino_misto"


def test_mesma_identidade_repetida_aceita():
    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(),
        resolver_url=lambda _: URL,
    )

    resultado = processador.resolver(
        mensagem(
            "https://tidd.ly/a",
            "https://tidd.ly/b",
        ),
        deteccao(marketplace=None),
    )

    assert resultado.status == "resolvido"
    assert resultado.id_produto == ID


def test_produtos_distintos_sao_ambiguos():
    destinos = {
        "https://tidd.ly/a": URL,
        "https://tidd.ly/b": ("https://www.kabum.com.br/" "produto/777777/outro"),
    }

    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(),
        resolver_url=lambda url: (destinos[url]),
    )

    resultado = processador.resolver(
        mensagem(*destinos.keys()),
        deteccao(marketplace=None),
    )

    assert resultado.status == "nao_suportado"

    assert resultado.motivo == "kabum_identidade_ambigua"


def test_falha_redirect_e_transitoria():
    def falhar(_):
        raise TimeoutError()

    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(),
        resolver_url=falhar,
    )

    resultado = processador.resolver(
        mensagem("https://tidd.ly/falha"),
        deteccao(marketplace=None),
    )

    assert resultado.status == "erro"


def test_preco_exato_valida():
    service = ServiceFake(resultado=resultado_valido())

    processador = ProcessadorKabumSocialScout(
        service=service,
    )

    resolucao = processador.resolver(
        mensagem(URL),
        deteccao(),
    )

    validacao = processador.validar(
        deteccao(),
        resolucao,
    )

    assert validacao.status == "validado"
    assert validacao.preco_oficial == 649.99

    assert validacao.titulo_oficial == "Monitor Gamer Oficial"

    assert validacao.preco_base_confere is True

    assert validacao.cupom_validado is False


def test_preco_divergente_rejeita():
    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(resultado=resultado_valido(preco=699.99)),
    )

    resolucao = processador.resolver(
        mensagem(URL),
        deteccao(),
    )

    validacao = processador.validar(
        deteccao(preco=649.99),
        resolucao,
    )

    assert validacao.status == "rejeitado"


def test_sem_preco_base_nao_confirma():
    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(resultado=resultado_valido()),
    )

    resolucao = processador.resolver(
        mensagem(URL),
        deteccao(),
    )

    validacao = processador.validar(
        deteccao(preco=None),
        resolucao,
    )

    assert validacao.status == "nao_verificavel"


def test_out_of_stock_nao_confirma():
    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(resultado=resultado_valido(disponivel=False)),
    )

    resolucao = processador.resolver(
        mensagem(URL),
        deteccao(),
    )

    validacao = processador.validar(
        deteccao(),
        resolucao,
    )

    assert validacao.status == "nao_verificavel"

    assert validacao.disponivel is False


def test_erro_pdp_e_transitorio():
    processador = ProcessadorKabumSocialScout(
        service=ServiceFake(
            resultado=ResultadoPrecoKabum(
                produto_id=ID,
                valido=False,
                motivo=("erro_kabum_pdp:" "TimeoutError"),
            )
        ),
    )

    resolucao = processador.resolver(
        mensagem(URL),
        deteccao(),
    )

    validacao = processador.validar(
        deteccao(),
        resolucao,
    )

    assert validacao.status == "erro"
