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
