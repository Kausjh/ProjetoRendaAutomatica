from models.resolucao_scout import ResolucaoScout
from models.sinal_scout import SinalScout
from repositories.historico_comercial_scout_repository import (
    HistoricoComercialScoutRepository,
)
from repositories.resolucoes_scout_repository import (
    ResolucoesScoutRepository,
)
from repositories.sinais_scout_repository import (
    SinaisScoutRepository,
)
from services.scout.ciclo_partner_scout import (
    CicloPartnerScout,
)
from services.scout.historico_comercial_scout import (
    HistoricoComercialScout,
)
from services.scout.radar_scout import RadarScout


class SensorMutavel:
    nome = "fake_partner"

    def __init__(
        self,
        sinal,
    ):
        self.sinal = sinal
        self.updated_since = None

    def buscar_sinais(
        self,
        updated_since=None,
    ):
        self.updated_since = updated_since

        return [
            self.sinal,
        ]


class ResolvedorFake:
    nome = "fake_resolver"

    def __init__(
        self,
        *,
        status="landing_page",
        marketplace="kabum",
        falhar=False,
    ):
        self.status = status
        self.marketplace = marketplace
        self.falhar = falhar
        self.chamadas = 0

    def suporta(
        self,
        sinal,
    ):
        return sinal.fonte == "awin"

    def resolver(
        self,
        sinal,
    ):
        self.chamadas += 1

        if self.falhar:
            raise RuntimeError("falha simulada")

        tipo_destino = "campanha" if self.status == "landing_page" else "produto"

        return ResolucaoScout(
            fonte=sinal.fonte,
            id_externo=sinal.id_externo,
            status=self.status,
            marketplace=self.marketplace,
            tipo_destino=tipo_destino,
            motivo="teste",
        )


def criar_sinal(
    *,
    id_externo="1",
    titulo=("10% de desconto em " "itens da linha PlayNinja."),
    codigo_voucher="GAMER10",
):
    return SinalScout(
        fonte="awin",
        id_externo=id_externo,
        tipo="voucher",
        titulo=titulo,
        url="https://www.kabum.com.br/",
        advertiser_id="123",
        advertiser_nome="Kabum BR",
        descricao=titulo,
        termos=titulo,
        codigo_voucher=codigo_voucher,
        regioes=("BR",),
    )


def montar(
    tmp_path,
    *,
    sinal=None,
    resolvedor=None,
    preexistente=False,
):
    sinal = sinal or criar_sinal()

    resolvedor = resolvedor or ResolvedorFake()

    banco_scout = tmp_path / "scout.sqlite3"

    banco_historico = tmp_path / "historico.sqlite3"

    sinais_repository = SinaisScoutRepository(banco_scout)

    resolucoes_repository = ResolucoesScoutRepository(banco_scout)

    if preexistente:
        sinais_repository.salvar(sinal)

    sensor = SensorMutavel(sinal)

    radar = RadarScout(
        sensores=[
            sensor,
        ],
        repository=(sinais_repository),
    )

    historico_repository = HistoricoComercialScoutRepository(banco_historico)

    historico = HistoricoComercialScout(historico_repository)

    ciclo = CicloPartnerScout(
        radar=radar,
        resolvedores=[
            resolvedor,
        ],
        resolucoes_repository=(resolucoes_repository),
        historico=historico,
    )

    return (
        ciclo,
        sensor,
        resolvedor,
        sinais_repository,
        resolucoes_repository,
        historico_repository,
    )


def test_radar_expoe_evento_novo(
    tmp_path,
):
    (
        ciclo,
        _sensor,
        _resolvedor,
        _sinais_repository,
        _resolucoes_repository,
        _historico_repository,
    ) = montar(tmp_path)

    resultado = ciclo.radar.executar()

    assert resultado.novos == 1
    assert len(resultado.eventos) == 1

    evento = resultado.eventos[0]

    assert evento.sensor == "fake_partner"

    assert evento.resultado == "novo"
    assert evento.sinal.id_externo == "1"


def test_radar_expoe_evento_inalterado(
    tmp_path,
):
    (
        ciclo,
        _sensor,
        _resolvedor,
        _sinais_repository,
        _resolucoes_repository,
        _historico_repository,
    ) = montar(
        tmp_path,
        preexistente=True,
    )

    resultado = ciclo.radar.executar()

    assert resultado.inalterados == 1
    assert len(resultado.eventos) == 1

    assert resultado.eventos[0].resultado == "inalterado"


def test_ciclo_partner_registra_novo_no_historico(
    tmp_path,
):
    (
        ciclo,
        _sensor,
        _resolvedor,
        _sinais_repository,
        _resolucoes_repository,
        historico_repository,
    ) = montar(tmp_path)

    resultado = ciclo.executar()

    assert resultado.eventos_comerciais == 1

    assert resultado.historicos_registrados == 1

    assert historico_repository.quantidade() == 1


def test_ciclo_partner_nao_registra_inalterado(
    tmp_path,
):
    (
        ciclo,
        _sensor,
        resolvedor,
        _sinais_repository,
        _resolucoes_repository,
        historico_repository,
    ) = montar(
        tmp_path,
        preexistente=True,
    )

    resultado = ciclo.executar()

    assert resultado.radar.inalterados == 1

    assert resultado.eventos_comerciais == 0

    assert resultado.historicos_registrados == 0

    assert historico_repository.quantidade() == 0

    assert resolvedor.chamadas == 0


def test_ciclo_partner_registra_atualizacao(
    tmp_path,
):
    (
        ciclo,
        sensor,
        _resolvedor,
        _sinais_repository,
        _resolucoes_repository,
        historico_repository,
    ) = montar(tmp_path)

    primeiro = ciclo.executar()

    assert primeiro.radar.novos == 1

    sensor.sinal = criar_sinal(
        titulo=("15% de desconto em " "itens da linha PlayNinja."),
        codigo_voucher="GAMER15",
    )

    segundo = ciclo.executar()

    assert segundo.radar.atualizados == 1

    assert segundo.eventos_comerciais == 1

    assert segundo.historicos_registrados == 1

    assert historico_repository.quantidade() == 2


def test_ciclo_partner_persiste_resolucao(
    tmp_path,
):
    (
        ciclo,
        _sensor,
        _resolvedor,
        _sinais_repository,
        resolucoes_repository,
        _historico_repository,
    ) = montar(tmp_path)

    resultado = ciclo.executar()

    assert resultado.resolucoes_persistidas == 1

    resolucao = resolucoes_repository.obter(
        "awin",
        "1",
    )

    assert resolucao is not None

    assert resolucao.marketplace == "kabum"

    assert resolucao.status == "landing_page"


def test_ciclo_partner_cria_plano_para_landing(
    tmp_path,
):
    (
        ciclo,
        _sensor,
        _resolvedor,
        _sinais_repository,
        _resolucoes_repository,
        historico_repository,
    ) = montar(tmp_path)

    resultado = ciclo.executar()

    assert resultado.planos_utilizaveis == 1

    observacoes = historico_repository.listar_observacoes()

    assert len(observacoes) == 1

    perfil = observacoes[0].perfil

    assert perfil.marketplace == "kabum"

    assert perfil.estrategia_discovery == "buscar_termos_kabum"

    assert perfil.termos_descoberta == ("PlayNinja",)


def test_ciclo_partner_nao_planeja_produto_resolvido(
    tmp_path,
):
    (
        ciclo,
        _sensor,
        _resolvedor,
        _sinais_repository,
        _resolucoes_repository,
        historico_repository,
    ) = montar(
        tmp_path,
        resolvedor=ResolvedorFake(
            status="resolvido",
            marketplace="kabum",
        ),
    )

    resultado = ciclo.executar()

    assert resultado.planos_utilizaveis == 0

    observacoes = historico_repository.listar_observacoes()

    perfil = observacoes[0].perfil

    assert perfil.marketplace == "kabum"

    assert perfil.tipo_destino == "produto"

    assert perfil.estrategia_discovery is None


def test_falha_resolvedor_preserva_evento_comercial(
    tmp_path,
):
    (
        ciclo,
        _sensor,
        _resolvedor,
        _sinais_repository,
        resolucoes_repository,
        historico_repository,
    ) = montar(
        tmp_path,
        resolvedor=ResolvedorFake(
            falhar=True,
        ),
    )

    resultado = ciclo.executar()

    assert resultado.falhas_resolucao == 1

    assert resultado.historicos_registrados == 1

    assert historico_repository.quantidade() == 1

    resolucao = resolucoes_repository.obter(
        "awin",
        "1",
    )

    assert resolucao is not None
    assert resolucao.status == "erro"

    observacao = historico_repository.listar_observacoes()[0]

    assert observacao.perfil.parceiro_nome == "Kabum BR"
