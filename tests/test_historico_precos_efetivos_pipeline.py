from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

from services.executor_pipeline import (
    ExecutorPipeline,
)


class ResultadoEfetivoFake:
    novo_preco_registrado = True
    preco_efetivo = 5951.07
    tipo_condicao = "valor_off_com_cupom"


class HistoricoEfetivoFake:
    def __init__(self):
        self.analisadas = []
        self.flushes = 0

    def analisar_e_registrar(
        self,
        oferta,
    ):
        self.analisadas.append(oferta)

        return ResultadoEfetivoFake()

    def salvar_pendentes(
        self,
    ):
        self.flushes += 1


def pipeline_minimo(
    service,
):
    pipeline = ExecutorPipeline.__new__(ExecutorPipeline)

    pipeline.historico_precos_efetivos_service = service

    return pipeline


def test_helper_delega_registro_ao_historico_efetivo():
    service = HistoricoEfetivoFake()

    pipeline = pipeline_minimo(service)

    oferta = object()

    resultado = pipeline._analisar_historico_efetivo(oferta)

    assert service.analisadas == [oferta]

    assert resultado.preco_efetivo == 5951.07


def test_helper_sem_service_e_totalmente_opcional():
    pipeline = pipeline_minimo(None)

    assert pipeline._analisar_historico_efetivo(object()) is None

    pipeline._salvar_historico_efetivo_pendente()


def test_flush_final_delega_para_service():
    service = HistoricoEfetivoFake()

    pipeline = pipeline_minimo(service)

    pipeline._salvar_historico_efetivo_pendente()

    assert service.flushes == 1


def test_executar_registra_e_faz_flush_do_historico_efetivo():
    fonte = inspect.getsource(ExecutorPipeline.executar)

    assert "self._analisar_historico_efetivo" in fonte

    assert "self._salvar_historico_efetivo_pendente()" in fonte

    assert '"novos_precos_efetivos_confirmados"' in fonte


def test_deal_score_continua_sem_historico_efetivo():
    fonte = textwrap.dedent(inspect.getsource(ExecutorPipeline.executar))

    arvore = ast.parse(fonte)

    chamadas = []

    for no in ast.walk(arvore):
        if not isinstance(
            no,
            ast.Call,
        ):
            continue

        func = no.func

        if not isinstance(
            func,
            ast.Attribute,
        ):
            continue

        if func.attr != "calcular":
            continue

        dono = func.value

        if not (
            isinstance(
                dono,
                ast.Attribute,
            )
            and dono.attr == "pontuador"
        ):
            continue

        chamadas.append(no)

    assert len(chamadas) == 1

    argumentos = {keyword.arg for keyword in chamadas[0].keywords if keyword.arg is not None}

    assert "resultado_historico" in argumentos

    assert "resultado_historico_efetivo" not in argumentos


def test_main_liga_repository_service_e_executor():
    raiz = Path(__file__).resolve().parents[1]

    main = (raiz / "main.py").read_text(
        encoding="utf-8-sig",
    )

    ast.parse(main)

    assert "HistoricoPrecosEfetivosRepository" in main

    assert "HistoricoPrecosEfetivosService" in main

    assert "precos_efetivos_confirmados.json" in main

    assert "historico_precos_efetivos_service=" in main


class ResultadoTelemetriaFake:
    def __init__(
        self,
        *,
        elegivel=True,
        baseline=0,
        novo_minimo=False,
        queda_mediana=0.0,
        queda_minimo=0.0,
        maturidade=0.0,
    ):
        self.elegivel = elegivel

        self.quantidade_registros_baseline = baseline

        self.novo_menor_preco = novo_minimo

        self.queda_vs_mediana_percentual = queda_mediana

        self.queda_vs_minimo_anterior_percentual = queda_minimo

        self.maturidade_baseline_percentual = maturidade


def test_telemetria_historico_efetivo_inicia_zerada():
    telemetria = ExecutorPipeline._criar_telemetria_historico_efetivo()

    assert telemetria == {
        "precos_com_baseline": 0,
        "novos_minimos": 0,
        "maior_queda_vs_mediana_percentual": 0.0,
        "maior_queda_vs_minimo_percentual": 0.0,
        "maior_maturidade_percentual": 0.0,
    }


def test_telemetria_historico_efetivo_agrega_metricas():
    telemetria = ExecutorPipeline._criar_telemetria_historico_efetivo()

    primeiro = ResultadoTelemetriaFake(
        baseline=3,
        novo_minimo=True,
        queda_mediana=5.0,
        queda_minimo=3.39,
        maturidade=30.0,
    )

    segundo = ResultadoTelemetriaFake(
        baseline=8,
        novo_minimo=False,
        queda_mediana=12.5,
        queda_minimo=1.5,
        maturidade=80.0,
    )

    ExecutorPipeline._atualizar_telemetria_historico_efetivo(
        telemetria,
        primeiro,
    )

    ExecutorPipeline._atualizar_telemetria_historico_efetivo(
        telemetria,
        segundo,
    )

    assert telemetria["precos_com_baseline"] == 2

    assert telemetria["novos_minimos"] == 1

    assert telemetria["maior_queda_vs_mediana_percentual"] == 12.5

    assert telemetria["maior_queda_vs_minimo_percentual"] == 3.39

    assert telemetria["maior_maturidade_percentual"] == 80.0


def test_telemetria_ignora_resultado_nao_elegivel():
    telemetria = ExecutorPipeline._criar_telemetria_historico_efetivo()

    resultado = ResultadoTelemetriaFake(
        elegivel=False,
        baseline=50,
        novo_minimo=True,
        queda_mediana=99.0,
        queda_minimo=99.0,
        maturidade=100.0,
    )

    ExecutorPipeline._atualizar_telemetria_historico_efetivo(
        telemetria,
        resultado,
    )

    assert telemetria == (ExecutorPipeline._criar_telemetria_historico_efetivo())


def test_relatorio_expoe_telemetria_observacional():
    fonte = inspect.getsource(ExecutorPipeline.executar)

    for campo in (
        "precos_efetivos_com_baseline",
        "novos_minimos_precos_efetivos",
        ("maior_queda_preco_efetivo_" "vs_mediana_percentual"),
        ("maior_queda_preco_efetivo_" "vs_minimo_percentual"),
        ("maior_maturidade_historico_" "efetivo_percentual"),
    ):
        assert campo in fonte
