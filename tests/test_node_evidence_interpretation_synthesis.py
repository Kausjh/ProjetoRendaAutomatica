import json

import pytest

from services.infra.node_evidence_interpretation_synthesis import (
    gerar_sintese_evidencias_interpretacoes_node,
    salvar_sintese_evidencias_interpretacoes_node,
)


def _resumo_item(
    codigo,
    *,
    observado=True,
    duracao=600.0,
    episodios=1,
    reaparecimentos=0,
    ausencias=0,
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
        "quantidade_episodios_observados": episodios,
        "reaparecimentos": reaparecimentos,
        "quantidade_periodos_ausentes": ausencias,
        "inicio_historico_truncado": truncado,
        "episodio_atual_aberto": observado,
        "periodo_ausencia_atual_aberto": (not observado),
        "duracao_estado_atual_segundos": duracao,
        "maior_duracao_observada_segundos": duracao,
        "maior_duracao_ausencia_segundos": None,
    }


def _qualidade_item(
    codigo,
    *,
    observado=True,
    duracao=600.0,
    episodios=1,
    reaparecimentos=0,
    ausencias=0,
    truncado=False,
    cobertura=100.0,
    faltantes=0,
    gaps_2x=0,
):
    return {
        "codigo": codigo,
        "observado_agora": observado,
        "primeira_evidencia": ("2026-09-10T16:00:00+00:00"),
        "ultima_evidencia": ("2026-09-10T16:10:00+00:00"),
        "registros_com_evidencia": 3,
        "registros_esperados_desde_primeira_evidencia": (3 + faltantes),
        "registros_ausentes_estimados": faltantes,
        "razao_amostras_percentual": cobertura,
        "cobertura_normalizada_percentual": cobertura,
        "maior_gap_evidencia_segundos": (700.0 if gaps_2x else 300.0),
        "gaps_igual_ou_acima_2x_cadencia": gaps_2x,
        "janela_evidencia_segundos": 600.0,
        "duracao_estado_atual_segundos": duracao,
        "duracao_estado_atual_percentual_janela": (100.0),
        "quantidade_episodios_observados": episodios,
        "reaparecimentos": reaparecimentos,
        "quantidade_periodos_ausentes": ausencias,
        "inicio_historico_truncado": truncado,
    }


def _resumo(
    itens,
    *,
    node_id="node-v129",
    referencia="2026-09-10T16:10:00+00:00",
):
    observadas = [item["codigo"] for item in itens if item["observado_agora"]]

    ausentes = [item["codigo"] for item in itens if not item["observado_agora"]]

    return {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "quantidade_interpretacoes": len(itens),
        "observadas_agora": len(observadas),
        "ausentes_agora": len(ausentes),
        "novas_no_ultimo_ciclo": 0,
        "continuaram_observadas": 0,
        "deixaram_de_ser_observadas": 0,
        "continuaram_ausentes": 0,
        "reapareceram_no_ultimo_ciclo": 0,
        "com_reaparecimento_historico": 0,
        "com_inicio_historico_truncado": 0,
        "observadas_por_maior_duracao_atual": observadas,
        "ausentes_por_maior_duracao_atual": ausentes,
        "interpretacoes": itens,
    }


def _qualidade(
    itens,
    *,
    node_id="node-v129",
    referencia="2026-09-10T16:10:00+00:00",
):
    ranking = [
        item["codigo"]
        for item in sorted(
            itens,
            key=lambda item: (
                item["cobertura_normalizada_percentual"],
                item["codigo"],
            ),
        )
    ]

    return {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "cadencia_nominal_segundos": 300.0,
        "inicio_historico": ("2026-09-10T16:00:00+00:00"),
        "fim_historico": referencia,
        "janela_historica_segundos": 600.0,
        "registros_observados": 3,
        "registros_esperados": 3,
        "registros_excedentes": 0,
        "razao_amostras_percentual": 100.0,
        "cobertura_normalizada_percentual": 100.0,
        "maior_gap_historico_segundos": 300.0,
        "gaps_igual_ou_acima_2x_cadencia": 0,
        "quantidade_interpretacoes": len(itens),
        "com_inicio_historico_truncado": 0,
        "interpretacoes_por_menor_cobertura_evidencia": (ranking),
        "interpretacoes": itens,
    }


def _gravar(
    caminho,
    dados,
):
    caminho.write_text(
        json.dumps(dados),
        encoding="utf-8",
    )


def _gerar(
    tmp_path,
    resumo,
    qualidade,
):
    caminho_resumo = tmp_path / "resumo.json"

    caminho_qualidade = tmp_path / "qualidade.json"

    _gravar(
        caminho_resumo,
        resumo,
    )

    _gravar(
        caminho_qualidade,
        qualidade,
    )

    return gerar_sintese_evidencias_interpretacoes_node(
        caminho_resumo,
        caminho_qualidade,
    )


def _por_codigo(
    sintese,
):
    return {item.codigo: item for item in sintese.interpretacoes}


def test_combina_persistencia_recorrencia_e_qualidade(
    tmp_path,
):
    sintese = _gerar(
        tmp_path,
        _resumo(
            [
                _resumo_item(
                    "a",
                    reaparecimentos=2,
                    episodios=3,
                    ausencias=2,
                )
            ]
        ),
        _qualidade(
            [
                _qualidade_item(
                    "a",
                    reaparecimentos=2,
                    episodios=3,
                    ausencias=2,
                )
            ]
        ),
    )

    item = _por_codigo(sintese)["a"]

    assert item.duracao_estado_atual_segundos == 600.0
    assert item.reaparecimentos == 2
    assert item.quantidade_episodios_observados == 3
    assert item.cobertura_evidencia_percentual == 100.0


def test_node_divergente_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="Node IDs divergentes",
    ):
        _gerar(
            tmp_path,
            _resumo(
                [_resumo_item("a")],
                node_id="node-a",
            ),
            _qualidade(
                [_qualidade_item("a")],
                node_id="node-b",
            ),
        )


def test_offset_equivalente_e_aceito(
    tmp_path,
):
    sintese = _gerar(
        tmp_path,
        _resumo(
            [_resumo_item("a")],
            referencia=("2026-09-10T13:10:00-03:00"),
        ),
        _qualidade(
            [_qualidade_item("a")],
            referencia=("2026-09-10T16:10:00+00:00"),
        ),
    )

    assert sintese.quantidade_interpretacoes == 1


def test_ciclo_divergente_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="ciclos diferentes",
    ):
        _gerar(
            tmp_path,
            _resumo(
                [_resumo_item("a")],
                referencia=("2026-09-10T16:10:00+00:00"),
            ),
            _qualidade(
                [_qualidade_item("a")],
                referencia=("2026-09-10T16:15:00+00:00"),
            ),
        )


def test_universo_divergente_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="Universo de interpretacoes divergente",
    ):
        _gerar(
            tmp_path,
            _resumo([_resumo_item("a")]),
            _qualidade([_qualidade_item("b")]),
        )


def test_estado_observado_divergente_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="Observacao atual divergente",
    ):
        _gerar(
            tmp_path,
            _resumo(
                [
                    _resumo_item(
                        "a",
                        observado=True,
                    )
                ]
            ),
            _qualidade(
                [
                    _qualidade_item(
                        "a",
                        observado=False,
                    )
                ]
            ),
        )


def test_duracao_divergente_e_rejeitada(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="Duracao do estado atual",
    ):
        _gerar(
            tmp_path,
            _resumo(
                [
                    _resumo_item(
                        "a",
                        duracao=600.0,
                    )
                ]
            ),
            _qualidade(
                [
                    _qualidade_item(
                        "a",
                        duracao=300.0,
                    )
                ]
            ),
        )


def test_recorrencia_e_truncamento_sao_preservados(
    tmp_path,
):
    sintese = _gerar(
        tmp_path,
        _resumo(
            [
                _resumo_item(
                    "a",
                    episodios=2,
                    reaparecimentos=1,
                    ausencias=1,
                    truncado=True,
                )
            ]
        ),
        _qualidade(
            [
                _qualidade_item(
                    "a",
                    episodios=2,
                    reaparecimentos=1,
                    ausencias=1,
                    truncado=True,
                )
            ]
        ),
    )

    item = _por_codigo(sintese)["a"]

    assert item.reaparecimentos == 1
    assert item.quantidade_periodos_ausentes == 1
    assert item.inicio_historico_truncado is True

    assert sintese.com_reaparecimento_historico == ("a",)

    assert sintese.com_inicio_historico_truncado == ("a",)


def test_lacunas_estimadas_sao_indexadas(
    tmp_path,
):
    sintese = _gerar(
        tmp_path,
        _resumo([_resumo_item("a")]),
        _qualidade(
            [
                _qualidade_item(
                    "a",
                    cobertura=75.0,
                    faltantes=1,
                )
            ]
        ),
    )

    assert sintese.com_lacunas_evidencia_estimadas == ("a",)


def test_gaps_2x_sao_indexados(
    tmp_path,
):
    sintese = _gerar(
        tmp_path,
        _resumo([_resumo_item("a")]),
        _qualidade(
            [
                _qualidade_item(
                    "a",
                    gaps_2x=1,
                )
            ]
        ),
    )

    assert sintese.com_gaps_igual_ou_acima_2x_cadencia == ("a",)


def test_rankings_sao_preservados(
    tmp_path,
):
    sintese = _gerar(
        tmp_path,
        _resumo(
            [
                _resumo_item("a"),
                _resumo_item("b"),
            ]
        ),
        _qualidade(
            [
                _qualidade_item(
                    "a",
                    cobertura=80.0,
                ),
                _qualidade_item(
                    "b",
                    cobertura=100.0,
                ),
            ]
        ),
    )

    assert sintese.observadas_por_maior_duracao_atual == (
        "a",
        "b",
    )

    assert sintese.por_menor_cobertura_evidencia == (
        "a",
        "b",
    )


def test_saida_atomica_e_sem_politica_operacional(
    tmp_path,
):
    sintese = _gerar(
        tmp_path,
        _resumo([_resumo_item("a")]),
        _qualidade([_qualidade_item("a")]),
    )

    caminho = tmp_path / "sintese.json"

    salvar_sintese_evidencias_interpretacoes_node(
        sintese,
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
