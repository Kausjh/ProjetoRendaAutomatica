# 63.8738, -149.7525

from __future__ import annotations

import inspect

import pytest

from models.oferta import Oferta
from services.curadoria_publicacao import CuradoriaPublicacao
from services.detector_anomalia_preco import (
    DetectorAnomaliaPreco,
)
from services.executor_pipeline import ExecutorPipeline
from services.historico_precos_service import (
    HistoricoPrecosService,
    ResultadoHistoricoPreco,
)


def oferta(
    link: str,
    preco: float = 400.0,
) -> Oferta:
    item = Oferta(
        nome=("Placa de V\u00eddeo NVIDIA " "GeForce RTX 5070 12GB"),
        loja="Marketplace",
        preco=preco,
        preco_antigo=None,
        link=link,
        imagem=None,
    )

    item.marketplace = "teste"
    item.id_produto = "PRODUTO-123"
    item.eh_nicho = True
    item.categoria = "Placa de v\u00eddeo"
    item.relevancia_nicho = 100.0

    return item


def historico(
    *,
    preco_anterior: float = 1000.0,
    menor_anterior: float = 900.0,
    mediana: float = 1000.0,
    variacao: float = -60.0,
    caiu: bool = True,
    menor: bool = True,
    registros: int = 6,
    baseline: int = 5,
) -> ResultadoHistoricoPreco:
    return ResultadoHistoricoPreco(
        primeiro_registro=False,
        preco_anterior=preco_anterior,
        menor_preco_anterior=menor_anterior,
        menor_preco_historico=menor,
        variacao_percentual=variacao,
        preco_caiu=caiu,
        preco_subiu=False,
        novo_preco_registrado=True,
        quantidade_registros=registros,
        preco_mediano_anterior=mediana,
        quantidade_registros_baseline=baseline,
    )


@pytest.mark.parametrize(
    "link",
    [
        "https://produto.mercadolivre.com.br/MLB-123",
        "https://s.shopee.com.br/abc123",
        "https://www.kabum.com.br/produto/123",
        "https://pt.aliexpress.com/item/100500123.html",
    ],
)
def test_bug_hunter_reconhece_marketplaces_oficiais(
    link,
):
    resultado = DetectorAnomaliaPreco().avaliar(
        oferta=oferta(link),
        resultado_historico=historico(),
    )

    assert resultado.detectada is True
    assert resultado.publicavel is True
    assert resultado.tipo == "possivel_preco_bugado"
    assert resultado.queda_percentual == 60.0


def test_mediana_mantem_bug_visivel_apos_preco_repetir():
    resultado = DetectorAnomaliaPreco().avaliar(
        oferta=oferta(
            "https://www.kabum.com.br/produto/123",
            preco=400.0,
        ),
        resultado_historico=historico(
            preco_anterior=400.0,
            menor_anterior=400.0,
            mediana=1000.0,
            variacao=0.0,
            caiu=False,
            menor=False,
        ),
    )

    assert resultado.detectada is True
    assert resultado.publicavel is True
    assert resultado.queda_percentual == 60.0

    assert any("mediana hist\u00f3rica" in motivo for motivo in resultado.motivos)


def test_dominio_falso_nao_e_aceito():
    resultado = DetectorAnomaliaPreco().avaliar(
        oferta=oferta("https://mercadolivre.com.br.evil.example/item"),
        resultado_historico=historico(),
    )

    assert resultado.detectada is True
    assert resultado.publicavel is False
    assert resultado.tipo == "anomalia_retida"


def test_queda_extrema_continua_retida():
    resultado = DetectorAnomaliaPreco().avaliar(
        oferta=oferta(
            "https://www.kabum.com.br/produto/123",
            preco=150.0,
        ),
        resultado_historico=historico(
            mediana=1000.0,
            variacao=-85.0,
        ),
    )

    assert resultado.detectada is True
    assert resultado.publicavel is False
    assert resultado.tipo == "anomalia_retida"
    assert resultado.queda_percentual == 85.0


class RepositoryFake:
    def __init__(self):
        self.registros = [
            {
                "preco": 1000.0,
                "coletado_em": "2026-09-01T10:00:00-03:00",
            },
            {
                "preco": 1100.0,
                "coletado_em": "2026-09-02T10:00:00-03:00",
            },
            {
                "preco": 900.0,
                "coletado_em": "2026-09-03T10:00:00-03:00",
            },
            {
                "preco": 1050.0,
                "coletado_em": "2026-09-04T10:00:00-03:00",
            },
        ]

    def obter_registros(
        self,
        chave_produto,
    ):
        return [dict(item) for item in self.registros]

    def registrar_preco(
        self,
        **kwargs,
    ):
        return False

    def salvar(
        self,
    ):
        return None


def test_historico_calcula_mediana_robusta():
    service = HistoricoPrecosService(
        repository=RepositoryFake(),
    )

    resultado = service.analisar_e_registrar(oferta("https://produto.mercadolivre.com.br/MLB-123"))

    assert resultado.preco_mediano_anterior == 1025.0
    assert resultado.quantidade_registros_baseline == 4


def _categoria_gpu_real() -> str:
    candidatos = [
        chave
        for chave in CuradoriaPublicacao.PRECO_MINIMO_PLAUSIVEL
        if CuradoriaPublicacao._normalizar(chave) == "placa de video"
    ]

    assert len(candidatos) == 1

    return candidatos[0]


def test_bug_validado_abaixo_do_piso_nao_e_descartado():
    item = oferta(
        "https://www.kabum.com.br/produto/123",
        preco=225.0,
    )

    item.categoria = _categoria_gpu_real()
    item.confianca_normalizacao = 95.0

    resultado_anomalia = DetectorAnomaliaPreco().avaliar(
        oferta=item,
        resultado_historico=historico(
            preco_anterior=500.0,
            menor_anterior=450.0,
            mediana=500.0,
            variacao=-55.0,
            caiu=True,
            menor=True,
            registros=6,
            baseline=5,
        ),
    )

    assert resultado_anomalia.detectada is True
    assert resultado_anomalia.publicavel is True
    assert resultado_anomalia.tipo == "possivel_preco_bugado"

    resultado_curadoria = CuradoriaPublicacao().analisar(item)

    assert resultado_curadoria.publicavel is True

    assert not any(
        "piso conservador" in bloqueio.casefold() for bloqueio in resultado_curadoria.bloqueios
    )

    assert any(
        "anomalia hist\u00f3rica validada" in motivo.casefold()
        for motivo in resultado_curadoria.motivos
    )


def test_preco_baixo_sem_evidencia_historica_continua_bloqueado():
    item = oferta(
        "https://www.kabum.com.br/produto/123",
        preco=225.0,
    )

    item.categoria = _categoria_gpu_real()
    item.confianca_normalizacao = 95.0

    resultado = CuradoriaPublicacao().analisar(item)

    assert resultado.publicavel is False

    assert any("piso conservador" in bloqueio.casefold() for bloqueio in resultado.bloqueios)


def test_pipeline_bug_hunter_roda_antes_da_curadoria():
    codigo = inspect.getsource(ExecutorPipeline.executar)

    detector = codigo.find("resultado_anomalia = " "self.detector_anomalia.avaliar")

    curadoria = codigo.find("resultado_curadoria = " "self.curadoria_publicacao.analisar")

    pontuador = codigo.find("pontuacao = " "self.pontuador.calcular")

    assert detector >= 0
    assert curadoria >= 0
    assert pontuador >= 0

    assert detector < curadoria < pontuador
