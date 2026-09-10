import json

import pytest

from services.infra.node_evidence_interpretation_temporal_quality import (
    analisar_qualidade_temporal_interpretacoes_node,
    salvar_qualidade_temporal_interpretacoes_node,
)


def _observacao(
    codigo,
    observado=True,
):
    return {
        "codigo": codigo,
        "observado_agora": observado,
    }


def _registro(
    referencia,
    observacoes,
    *,
    node_id="node-v127",
):
    return {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "quantidade_observacoes_conhecidas": len(observacoes),
        "quantidade_observadas_agora": sum(1 for item in observacoes if item["observado_agora"]),
        "observacoes": observacoes,
    }


def _resumo_item(
    codigo,
    *,
    observado=True,
    duracao=600.0,
    truncado=False,
):
    return {
        "codigo": codigo,
        "categoria": "teste",
        "sujeito": codigo,
        "descricao": f"Descricao {codigo}",
        "observado_agora": observado,
        "transicao_ultimo_ciclo": ("continua_observado" if observado else "continua_nao_observado"),
        "primeira_observacao": ("2026-09-10T16:00:00+00:00"),
        "inicio_sequencia_atual": ("2026-09-10T16:00:00+00:00"),
        "ultima_observacao": ("2026-09-10T16:10:00+00:00"),
        "deixou_de_ser_observado_em": None,
        "observacoes_consecutivas": 3,
        "observacoes_totais": 3,
        "ciclos_ausente_consecutivos": 0,
        "quantidade_episodios_observados": 1,
        "reaparecimentos": 0,
        "quantidade_periodos_ausentes": (0 if observado else 1),
        "inicio_historico_truncado": truncado,
        "episodio_atual_aberto": observado,
        "periodo_ausencia_atual_aberto": (not observado),
        "duracao_estado_atual_segundos": duracao,
        "maior_duracao_observada_segundos": 600.0,
        "maior_duracao_ausencia_segundos": None,
    }


def _resumo(
    itens,
    *,
    node_id="node-v127",
    referencia="2026-09-10T16:10:00+00:00",
):
    return {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "quantidade_interpretacoes": len(itens),
        "observadas_agora": sum(1 for item in itens if item["observado_agora"]),
        "ausentes_agora": sum(1 for item in itens if not item["observado_agora"]),
        "novas_no_ultimo_ciclo": 0,
        "continuaram_observadas": 0,
        "deixaram_de_ser_observadas": 0,
        "continuaram_ausentes": 0,
        "reapareceram_no_ultimo_ciclo": 0,
        "com_reaparecimento_historico": 0,
        "com_inicio_historico_truncado": sum(
            1 for item in itens if item["inicio_historico_truncado"]
        ),
        "observadas_por_maior_duracao_atual": [],
        "ausentes_por_maior_duracao_atual": [],
        "interpretacoes": itens,
    }


def _gravar_json(
    caminho,
    dados,
):
    caminho.write_text(
        json.dumps(dados),
        encoding="utf-8",
    )


def _gravar_historico(
    diretorio,
    registros,
):
    diretorio.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho = diretorio / "2026-09-10.jsonl"

    caminho.write_text(
        "".join(json.dumps(item) + "\n" for item in registros),
        encoding="utf-8",
    )


def _analisar(
    tmp_path,
    resumo,
    registros,
    *,
    cadencia=300.0,
):
    caminho_resumo = tmp_path / "resumo.json"

    diretorio = tmp_path / "historico"

    _gravar_json(
        caminho_resumo,
        resumo,
    )

    _gravar_historico(
        diretorio,
        registros,
    )

    return analisar_qualidade_temporal_interpretacoes_node(
        caminho_resumo,
        diretorio,
        cadencia_nominal_segundos=cadencia,
    )


def _por_codigo(
    analise,
):
    return {item.codigo: item for item in analise.interpretacoes}


def test_cobertura_global_exata_na_cadencia(
    tmp_path,
):
    registros = [
        _registro(
            "2026-09-10T16:00:00+00:00",
            [_observacao("a")],
        ),
        _registro(
            "2026-09-10T16:05:00+00:00",
            [_observacao("a")],
        ),
        _registro(
            "2026-09-10T16:10:00+00:00",
            [_observacao("a")],
        ),
    ]

    analise = _analisar(
        tmp_path,
        _resumo([_resumo_item("a")]),
        registros,
    )

    assert analise.registros_observados == 3
    assert analise.registros_esperados == 3
    assert analise.cobertura_normalizada_percentual == 100.0


def test_amostras_excedentes_preservam_razao_bruta(
    tmp_path,
):
    registros = [
        _registro(
            "2026-09-10T16:00:00+00:00",
            [_observacao("a")],
        ),
        _registro(
            "2026-09-10T16:02:00+00:00",
            [_observacao("a")],
        ),
        _registro(
            "2026-09-10T16:05:00+00:00",
            [_observacao("a")],
        ),
    ]

    analise = _analisar(
        tmp_path,
        _resumo(
            [_resumo_item("a")],
            referencia=("2026-09-10T16:05:00+00:00"),
        ),
        registros,
    )

    assert analise.registros_esperados == 2
    assert analise.registros_excedentes == 1
    assert analise.razao_amostras_percentual == 150.0
    assert analise.cobertura_normalizada_percentual == 100.0


def test_gap_global_de_duas_cadencias_e_contado(
    tmp_path,
):
    registros = [
        _registro(
            "2026-09-10T16:00:00+00:00",
            [_observacao("a")],
        ),
        _registro(
            "2026-09-10T16:10:00+00:00",
            [_observacao("a")],
        ),
    ]

    analise = _analisar(
        tmp_path,
        _resumo([_resumo_item("a")]),
        registros,
    )

    assert analise.maior_gap_historico_segundos == 600.0
    assert analise.gaps_igual_ou_acima_2x_cadencia == 1


def test_cobertura_individual_detecta_evidencia_ausente(
    tmp_path,
):
    registros = [
        _registro(
            "2026-09-10T16:00:00+00:00",
            [_observacao("a")],
        ),
        _registro(
            "2026-09-10T16:05:00+00:00",
            [],
        ),
        _registro(
            "2026-09-10T16:10:00+00:00",
            [_observacao("a")],
        ),
    ]

    analise = _analisar(
        tmp_path,
        _resumo([_resumo_item("a")]),
        registros,
    )

    item = _por_codigo(analise)["a"]

    assert item.registros_com_evidencia == 2
    assert item.registros_esperados_desde_primeira_evidencia == 3
    assert item.registros_ausentes_estimados == 1
    assert item.cobertura_normalizada_percentual == pytest.approx(66.6666666667)


def test_ranking_prioriza_menor_cobertura(
    tmp_path,
):
    registros = [
        _registro(
            "2026-09-10T16:00:00+00:00",
            [
                _observacao("a"),
                _observacao("b"),
            ],
        ),
        _registro(
            "2026-09-10T16:05:00+00:00",
            [
                _observacao("b"),
            ],
        ),
        _registro(
            "2026-09-10T16:10:00+00:00",
            [
                _observacao("a"),
                _observacao("b"),
            ],
        ),
    ]

    analise = _analisar(
        tmp_path,
        _resumo(
            [
                _resumo_item("a"),
                _resumo_item("b"),
            ]
        ),
        registros,
    )

    assert analise.interpretacoes_por_menor_cobertura_evidencia[0] == "a"


def test_inicio_truncado_e_preservado(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        _resumo(
            [
                _resumo_item(
                    "a",
                    truncado=True,
                )
            ],
            referencia=("2026-09-10T16:00:00+00:00"),
        ),
        [
            _registro(
                "2026-09-10T16:00:00+00:00",
                [_observacao("a")],
            )
        ],
    )

    assert analise.com_inicio_historico_truncado == 1

    assert _por_codigo(analise)["a"].inicio_historico_truncado is True


def test_offset_equivalente_no_ciclo_final_e_aceito(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        _resumo(
            [_resumo_item("a")],
            referencia=("2026-09-10T13:10:00-03:00"),
        ),
        [
            _registro(
                "2026-09-10T16:00:00+00:00",
                [_observacao("a")],
            ),
            _registro(
                "2026-09-10T16:05:00+00:00",
                [_observacao("a")],
            ),
            _registro(
                "2026-09-10T16:10:00+00:00",
                [_observacao("a")],
            ),
        ],
    )

    assert analise.quantidade_interpretacoes == 1


def test_ciclo_final_divergente_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="ciclos diferentes",
    ):
        _analisar(
            tmp_path,
            _resumo(
                [_resumo_item("a")],
                referencia=("2026-09-10T16:15:00+00:00"),
            ),
            [
                _registro(
                    "2026-09-10T16:00:00+00:00",
                    [_observacao("a")],
                ),
                _registro(
                    "2026-09-10T16:10:00+00:00",
                    [_observacao("a")],
                ),
            ],
        )


def test_duplicate_equivalente_e_idempotente(
    tmp_path,
):
    primeiro = _registro(
        "2026-09-10T16:00:00+00:00",
        [_observacao("a")],
    )

    segundo = dict(primeiro)

    segundo["referencia_temporal"] = "2026-09-10T13:00:00-03:00"

    analise = _analisar(
        tmp_path,
        _resumo(
            [_resumo_item("a")],
            referencia=("2026-09-10T16:00:00+00:00"),
        ),
        [
            primeiro,
            segundo,
        ],
    )

    assert analise.registros_observados == 1


def test_duplicate_inconsistente_e_rejeitado(
    tmp_path,
):
    primeiro = _registro(
        "2026-09-10T16:00:00+00:00",
        [_observacao("a", True)],
    )

    segundo = _registro(
        "2026-09-10T13:00:00-03:00",
        [_observacao("a", False)],
    )

    with pytest.raises(
        ValueError,
        match="mesmo instante",
    ):
        _analisar(
            tmp_path,
            _resumo(
                [_resumo_item("a")],
                referencia=("2026-09-10T16:00:00+00:00"),
            ),
            [
                primeiro,
                segundo,
            ],
        )


def test_node_sem_historico_correspondente_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="node atual",
    ):
        _analisar(
            tmp_path,
            _resumo(
                [_resumo_item("a")],
                node_id="node-atual",
                referencia=("2026-09-10T16:00:00+00:00"),
            ),
            [
                _registro(
                    "2026-09-10T16:00:00+00:00",
                    [_observacao("a")],
                    node_id="node-antigo",
                )
            ],
        )


def test_saida_atomica_e_sem_politica_operacional(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        _resumo(
            [_resumo_item("a")],
            referencia=("2026-09-10T16:00:00+00:00"),
        ),
        [
            _registro(
                "2026-09-10T16:00:00+00:00",
                [_observacao("a")],
            )
        ],
    )

    caminho = tmp_path / "qualidade.json"

    salvar_qualidade_temporal_interpretacoes_node(
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
