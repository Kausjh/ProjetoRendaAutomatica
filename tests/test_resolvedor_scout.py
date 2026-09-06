from unittest.mock import Mock, patch

import requests

from models.resolucao_scout import ResolucaoScout
from models.sinal_scout import SinalScout
from repositories.resolucoes_scout_repository import (
    ResolucoesScoutRepository,
)
from repositories.sinais_scout_repository import (
    SinaisScoutRepository,
)
from services.scout.awin_destino_resolver import (
    AwinDestinoResolver,
)
from services.scout.resolvedor_scout import (
    ResolvedorRadarScout,
)


def criar_sinal(
    *,
    id_externo: str = "1",
    url: str = "https://exemplo.com/",
    url_tracking: str | None = None,
) -> SinalScout:
    return SinalScout(
        fonte="awin",
        id_externo=id_externo,
        tipo="promotion",
        titulo="Promocao de teste",
        url=url,
        url_tracking=url_tracking,
        advertiser_id="123",
        advertiser_nome="Teste",
        regioes=("BR",),
    )


def test_repository_sinais_lista_payload_salvo(
    tmp_path,
):
    repository = SinaisScoutRepository(tmp_path / "scout.sqlite3")

    sinal = criar_sinal(url=("https://www.kabum.com.br/" "produto/123456/teste"))

    repository.salvar(sinal)

    sinais = repository.listar()

    assert sinais == [sinal]
    assert sinais[0].regioes == ("BR",)


def test_resolvedor_identifica_produto_kabum():
    sinal = criar_sinal(url=("https://www.kabum.com.br/" "produto/123456/" "produto-de-teste"))

    resolvedor = AwinDestinoResolver()

    with patch("services.scout." "awin_destino_resolver." "requests.get") as requisicao:
        resultado = resolvedor.resolver(sinal)

    requisicao.assert_not_called()

    assert resultado.status == ("resolvido")

    assert resultado.marketplace == ("kabum")

    assert resultado.id_produto == ("123456")


def test_resolvedor_identifica_produto_aliexpress():
    sinal = criar_sinal(url=("https://pt.aliexpress.com/" "item/1005001234567890.html"))

    resultado = AwinDestinoResolver().resolver(sinal)

    assert resultado.status == ("resolvido")

    assert resultado.marketplace == ("aliexpress")

    assert resultado.id_produto == ("1005001234567890")


def test_resolvedor_identifica_landing_page():
    sinal = criar_sinal(url=("https://www.kabum.com.br/" "hardware"))

    resultado = AwinDestinoResolver().resolver(sinal)

    assert resultado.status == ("landing_page")

    assert resultado.marketplace == ("kabum")

    assert resultado.id_produto is None


def test_resolvedor_segue_tracking_ate_marketplace():
    sinal = criar_sinal(
        url=("https://www.awin1.com/" "promocao"),
        url_tracking=("https://www.awin1.com/" "cread.php?teste=1"),
    )

    resposta = Mock()

    resposta.url = "https://www.kabum.com.br/" "produto/987654/teste"

    resposta.status_code = 200

    with patch(
        "services.scout." "awin_destino_resolver." "requests.get",
        return_value=resposta,
    ):
        resultado = AwinDestinoResolver().resolver(sinal)

    assert resultado.status == ("resolvido")

    assert resultado.marketplace == ("kabum")

    assert resultado.id_produto == ("987654")

    resposta.close.assert_called()


def test_resolvedor_marca_destino_desconhecido():
    sinal = criar_sinal(url=("https://www.awin1.com/" "promocao"))

    resposta = Mock()

    resposta.url = "https://loja-exemplo.com/" "promocao"

    resposta.status_code = 200

    with patch(
        "services.scout." "awin_destino_resolver." "requests.get",
        return_value=resposta,
    ):
        resultado = AwinDestinoResolver().resolver(sinal)

    assert resultado.status == ("nao_suportado")


def test_resolvedor_trata_falha_http():
    sinal = criar_sinal(url=("https://www.awin1.com/" "promocao"))

    with patch(
        "services.scout." "awin_destino_resolver." "requests.get",
        side_effect=(requests.RequestException("falha simulada")),
    ):
        resultado = AwinDestinoResolver().resolver(sinal)

    assert resultado.status == ("erro")


def test_repository_resolucoes_persiste_resultado(
    tmp_path,
):
    repository = ResolucoesScoutRepository(tmp_path / "scout.sqlite3")

    resolucao = ResolucaoScout(
        fonte="awin",
        id_externo="1",
        status="resolvido",
        marketplace="kabum",
        tipo_destino="produto",
        url_destino=("https://www.kabum.com.br/" "produto/1/teste"),
        id_produto="1",
        http_status=200,
        motivo="produto_identificado",
    )

    repository.salvar(resolucao)

    recuperada = repository.obter(
        "awin",
        "1",
    )

    assert recuperada == resolucao
    assert repository.quantidade() == 1


class ResolvedorFake:
    nome = "fake"

    def suporta(
        self,
        sinal,
    ):
        return True

    def resolver(
        self,
        sinal,
    ):
        return ResolucaoScout(
            fonte=sinal.fonte,
            id_externo=(sinal.id_externo),
            status="resolvido",
            marketplace="kabum",
            tipo_destino="produto",
            id_produto="1",
            motivo="teste",
        )


def test_orquestrador_nao_reprocessa_existente(
    tmp_path,
):
    banco = tmp_path / "scout.sqlite3"

    sinais_repository = SinaisScoutRepository(banco)

    resolucoes_repository = ResolucoesScoutRepository(banco)

    sinais_repository.salvar(criar_sinal())

    servico = ResolvedorRadarScout(
        resolvedores=[ResolvedorFake()],
        sinais_repository=(sinais_repository),
        resolucoes_repository=(resolucoes_repository),
    )

    primeiro = servico.executar()

    segundo = servico.executar()

    assert primeiro.processados == 1
    assert primeiro.resolvidos == 1

    assert segundo.processados == 0
    assert segundo.ignorados_existentes == 1
