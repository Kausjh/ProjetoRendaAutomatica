import json

import pytest

from services.infra.node_evidence_interpretation_synthesis_history_analysis import (
    analisar_historico_sinteses_interpretacoes_node,
    salvar_analise_historico_sinteses_interpretacoes_node,
)


def _item(
    codigo,
    *,
    observado=True,
    reaparecimentos=0,
    cobertura=100.0,
    maior_gap=300.0,
):
    return {
        "codigo": codigo,
        "categoria": "teste",
        "sujeito": codigo,
        "descricao": f"Descricao {codigo}",
        "observado_agora": observado,
        "transicao_ultimo_ciclo": "teste",
        "duracao_estado_atual_segundos": 300.0,
        "duracao_estado_atual_percentual_janela": 100.0,
        "quantidade_episodios_observados": 1,
        "reaparecimentos": reaparecimentos,
        "quantidade_periodos_ausentes": 0,
        "inicio_historico_truncado": False,
        "primeira_evidencia": "2026-09-10T16:00:00+00:00",
        "ultima_evidencia": "2026-09-10T16:00:00+00:00",
        "janela_evidencia_segundos": 300.0,
        "registros_com_evidencia": 1,
        "registros_esperados_desde_primeira_evidencia": 1,
        "registros_ausentes_estimados": 0,
        "razao_amostras_percentual": cobertura,
        "cobertura_evidencia_percentual": cobertura,
        "maior_gap_evidencia_segundos": maior_gap,
        "gaps_igual_ou_acima_2x_cadencia": 0,
    }


def _sintese(
    referencia,
    itens,
    *,
    node_id="node-v133",
    lacunas=(),
    gaps=(),
    truncados=(),
):
    universo = {item["codigo"] for item in itens}

    observadas = [item["codigo"] for item in itens if item["observado_agora"]]

    ausentes = [item["codigo"] for item in itens if not item["observado_agora"]]

    reaparecimento = [item["codigo"] for item in itens if item["reaparecimentos"] > 0]

    assert set(lacunas).issubset(universo)
    assert set(gaps).issubset(universo)
    assert set(truncados).issubset(universo)

    return {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "cadencia_nominal_segundos": 300.0,
        "quantidade_interpretacoes": len(itens),
        "observadas_agora": len(observadas),
        "ausentes_agora": len(ausentes),
        "com_reaparecimento_historico": reaparecimento,
        "com_lacunas_evidencia_estimadas": list(lacunas),
        "com_gaps_igual_ou_acima_2x_cadencia": list(gaps),
        "com_inicio_historico_truncado": list(truncados),
        "observadas_por_maior_duracao_atual": observadas,
        "ausentes_por_maior_duracao_atual": ausentes,
        "por_menor_cobertura_evidencia": [item["codigo"] for item in itens],
        "interpretacoes": itens,
    }


def _gravar_historico(
    tmp_path,
    registros,
):
    diretorio = tmp_path / "historico"

    diretorio.mkdir(
        parents=True,
    )

    caminho = diretorio / "2026-09-10.jsonl"

    caminho.write_text(
        "".join(json.dumps(registro) + "\n" for registro in registros),
        encoding="utf-8",
    )

    return diretorio


def _analisar(
    tmp_path,
    registros,
):
    diretorio = _gravar_historico(
        tmp_path,
        registros,
    )

    return analisar_historico_sinteses_interpretacoes_node(diretorio)


def _interpretacao(
    analise,
    codigo,
):
    return next(item for item in analise.interpretacoes if item.codigo == codigo)


def test_usa_apenas_node_mais_recente(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _sintese(
                "2026-09-10T17:00:00+00:00",
                [_item("antigo")],
                node_id="node-antigo",
            ),
            _sintese(
                "2026-09-10T17:05:00+00:00",
                [_item("atual")],
                node_id="node-atual",
            ),
        ],
    )

    assert analise.node_id == "node-atual"
    assert analise.quantidade_registros == 1
    assert analise.quantidade_interpretacoes_distintas == 1


def test_ordena_registros_temporalmente(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _sintese(
                "2026-09-10T17:10:00+00:00",
                [_item("a", observado=False)],
            ),
            _sintese(
                "2026-09-10T17:05:00+00:00",
                [_item("a", observado=True)],
            ),
        ],
    )

    assert analise.inicio_historico.endswith("17:05:00+00:00")

    assert analise.fim_historico.endswith("17:10:00+00:00")


def test_offset_equivalente_duplicado_e_idempotente(
    tmp_path,
):
    primeiro = _sintese(
        "2026-09-10T17:05:00+00:00",
        [_item("a")],
    )

    segundo = _sintese(
        "2026-09-10T14:05:00-03:00",
        [_item("a")],
    )

    segundo["interpretacoes"][0]["primeira_evidencia"] = "2026-09-10T13:00:00-03:00"

    primeiro["interpretacoes"][0]["primeira_evidencia"] = "2026-09-10T16:00:00+00:00"

    analise = _analisar(
        tmp_path,
        [
            primeiro,
            segundo,
        ],
    )

    assert analise.quantidade_registros == 1


def test_mesmo_instante_divergente_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="mesmo instante",
    ):
        _analisar(
            tmp_path,
            [
                _sintese(
                    "2026-09-10T17:05:00+00:00",
                    [_item("a", observado=True)],
                ),
                _sintese(
                    "2026-09-10T17:05:00+00:00",
                    [_item("a", observado=False)],
                ),
            ],
        )


def test_detecta_novas_e_removidas(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _sintese(
                "2026-09-10T17:05:00+00:00",
                [_item("a")],
            ),
            _sintese(
                "2026-09-10T17:10:00+00:00",
                [_item("b")],
            ),
        ],
    )

    ultimo = analise.ciclos[-1]

    assert ultimo.novas_interpretacoes == ("b",)
    assert ultimo.interpretacoes_removidas == ("a",)

    assert analise.novas_interpretacoes_total == 1
    assert analise.interpretacoes_removidas_total == 1


def test_detecta_mudanca_estado_observado(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _sintese(
                "2026-09-10T17:05:00+00:00",
                [_item("a", observado=False)],
            ),
            _sintese(
                "2026-09-10T17:10:00+00:00",
                [_item("a", observado=True)],
            ),
            _sintese(
                "2026-09-10T17:15:00+00:00",
                [_item("a", observado=False)],
            ),
        ],
    )

    assert analise.ciclos[1].passaram_a_ser_observadas == ("a",)

    assert analise.ciclos[2].deixaram_de_ser_observadas == ("a",)

    assert analise.mudancas_estado_observado_total == 2

    item = _interpretacao(
        analise,
        "a",
    )

    assert item.mudancas_estado_observado == 2


def test_ausencia_do_codigo_nao_inventa_mudanca_de_estado(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _sintese(
                "2026-09-10T17:05:00+00:00",
                [_item("a", observado=True)],
            ),
            _sintese(
                "2026-09-10T17:10:00+00:00",
                [_item("b")],
            ),
            _sintese(
                "2026-09-10T17:15:00+00:00",
                [_item("a", observado=False)],
            ),
        ],
    )

    item = _interpretacao(
        analise,
        "a",
    )

    assert item.mudancas_estado_observado == 0


def test_detecta_incremento_reaparecimento(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _sintese(
                "2026-09-10T17:05:00+00:00",
                [_item("a", reaparecimentos=0)],
            ),
            _sintese(
                "2026-09-10T17:10:00+00:00",
                [_item("a", reaparecimentos=1)],
            ),
        ],
    )

    assert analise.ciclos[-1].reaparecimentos_incrementados == ("a",)

    assert analise.incrementos_reaparecimento_total == 1

    assert (
        _interpretacao(
            analise,
            "a",
        ).incrementos_reaparecimento
        == 1
    )


def test_calcula_estatisticas_de_cobertura_e_gap(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _sintese(
                "2026-09-10T17:05:00+00:00",
                [
                    _item(
                        "a",
                        cobertura=80.0,
                        maior_gap=700.0,
                    ),
                    _item(
                        "b",
                        cobertura=100.0,
                        maior_gap=300.0,
                    ),
                ],
            )
        ],
    )

    assert analise.cobertura_minima_historica_percentual == 80.0

    assert analise.cobertura_media_historica_percentual == 90.0

    assert analise.maior_gap_evidencia_historico_segundos == 700.0


def test_conta_ciclos_com_lacuna_gap_e_truncamento(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _sintese(
                "2026-09-10T17:05:00+00:00",
                [_item("a")],
                lacunas=("a",),
                gaps=("a",),
                truncados=("a",),
            ),
            _sintese(
                "2026-09-10T17:10:00+00:00",
                [_item("a")],
            ),
        ],
    )

    assert analise.ciclos_com_lacunas_evidencia == 1

    assert analise.ciclos_com_gaps_igual_ou_acima_2x_cadencia == 1

    assert analise.ciclos_com_inicio_historico_truncado == 1


def test_contagem_inconsistente_e_rejeitada(
    tmp_path,
):
    registro = _sintese(
        "2026-09-10T17:05:00+00:00",
        [_item("a")],
    )

    registro["observadas_agora"] = 0

    with pytest.raises(
        ValueError,
        match="Contagens observadas/ausentes inconsistentes",
    ):
        _analisar(
            tmp_path,
            [registro],
        )


def test_saida_atomica_e_sem_politica_operacional(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _sintese(
                "2026-09-10T17:05:00+00:00",
                [_item("a")],
            )
        ],
    )

    caminho = tmp_path / "analise.json"

    salvar_analise_historico_sinteses_interpretacoes_node(
        analise,
        caminho,
    )

    assert caminho.exists()

    assert not caminho.with_suffix(".json.tmp").exists()

    texto = caminho.read_text(encoding="utf-8")

    for termo in (
        "status_saude",
        "precisa_reiniciar",
        "reboot_recomendado",
        "acao_recomendada",
        "saudavel",
        "degradado",
        "critico",
        "severidade",
    ):
        assert termo not in texto
