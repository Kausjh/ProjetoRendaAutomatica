import json

import pytest

from services.infra.node_evidence_interpretation_temporal_summary import (
    gerar_resumo_temporal_interpretacoes_node,
    salvar_resumo_temporal_interpretacoes_node,
)


def _estado_item(
    codigo,
    *,
    observado=True,
    transicao="continua_observado",
):
    return {
        "codigo": codigo,
        "categoria": "teste",
        "sujeito": codigo,
        "descricao": f"Descricao {codigo}",
        "primeira_observacao": ("2026-09-10T16:00:00+00:00"),
        "inicio_sequencia_atual": ("2026-09-10T16:00:00+00:00"),
        "ultima_observacao": ("2026-09-10T16:10:00+00:00"),
        "observado_agora": observado,
        "observacoes_consecutivas": (3 if observado else 0),
        "observacoes_totais": 3,
        "ciclos_ausente_consecutivos": (0 if observado else 1),
        "deixou_de_ser_observado_em": (None if observado else "2026-09-10T16:10:00+00:00"),
        "transicao_ultimo_ciclo": transicao,
        "dados_mais_recentes": {},
        "fontes_mais_recentes": [],
    }


def _historico_item(
    codigo,
    *,
    observado=True,
    reaparecimentos=0,
    duracao=600.0,
    inicio_confirmado=True,
):
    episodio = {
        "inicio": ("2026-09-10T16:00:00+00:00"),
        "fim": ("2026-09-10T16:10:00+00:00"),
        "inicio_confirmado": inicio_confirmado,
        "fim_confirmado": (not observado),
        "duracao_acompanhada_segundos": (600.0),
    }

    ausencia = {
        "inicio": ("2026-09-10T16:10:00+00:00"),
        "fim": ("2026-09-10T16:10:00+00:00"),
        "inicio_confirmado": True,
        "fim_confirmado": False,
        "duracao_acompanhada_segundos": (duracao),
    }

    return {
        "codigo": codigo,
        "categoria": "teste",
        "sujeito": codigo,
        "descricao": f"Descricao {codigo}",
        "primeira_referencia": ("2026-09-10T16:00:00+00:00"),
        "ultima_referencia": ("2026-09-10T16:10:00+00:00"),
        "observado_agora": observado,
        "observacoes_explicitas": 3,
        "quantidade_episodios_observados": (1 + reaparecimentos),
        "reaparecimentos": reaparecimentos,
        "quantidade_periodos_ausentes": (0 if observado else 1),
        "episodio_atual_aberto": observado,
        "periodo_ausencia_atual_aberto": (not observado),
        "duracao_episodio_atual_segundos": (duracao if observado else None),
        "duracao_ausencia_atual_segundos": (None if observado else duracao),
        "maior_duracao_observada_segundos": (600.0),
        "maior_duracao_ausencia_segundos": (duracao if not observado else None),
        "episodios_observados": [episodio],
        "periodos_ausentes": ([] if observado else [ausencia]),
    }


def _estado(
    itens,
    *,
    node_id="node-v125",
    referencia="2026-09-10T16:10:00+00:00",
):
    return {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "quantidade_observacoes_conhecidas": len(itens),
        "quantidade_observadas_agora": sum(1 for item in itens if item["observado_agora"]),
        "observacoes": itens,
    }


def _analise(
    itens,
    *,
    node_id="node-v125",
    referencia="2026-09-10T16:10:00+00:00",
):
    return {
        "versao_schema": 1,
        "node_id": node_id,
        "inicio_periodo": ("2026-09-10T16:00:00+00:00"),
        "fim_periodo": referencia,
        "quantidade_registros": 3,
        "quantidade_interpretacoes": len(itens),
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
    estado,
    analise,
):
    caminho_estado = tmp_path / "estado.json"

    caminho_analise = tmp_path / "analise.json"

    _gravar(
        caminho_estado,
        estado,
    )

    _gravar(
        caminho_analise,
        analise,
    )

    return gerar_resumo_temporal_interpretacoes_node(
        caminho_estado,
        caminho_analise,
    )


def _por_codigo(
    resumo,
):
    return {item.codigo: item for item in resumo.interpretacoes}


def test_combina_estado_atual_e_historico(
    tmp_path,
):
    resumo = _gerar(
        tmp_path,
        _estado([_estado_item("a")]),
        _analise([_historico_item("a")]),
    )

    item = _por_codigo(resumo)["a"]

    assert resumo.quantidade_interpretacoes == 1
    assert item.observado_agora is True
    assert item.quantidade_episodios_observados == 1


def test_conta_transicoes_do_ultimo_ciclo(
    tmp_path,
):
    estados = [
        _estado_item(
            "novo",
            transicao="novo",
        ),
        _estado_item(
            "continuo",
            transicao="continua_observado",
        ),
        _estado_item(
            "sumiu",
            observado=False,
            transicao="deixou_de_ser_observado",
        ),
        _estado_item(
            "ausente",
            observado=False,
            transicao="continua_nao_observado",
        ),
        _estado_item(
            "voltou",
            transicao="reapareceu",
        ),
    ]

    historicos = [
        _historico_item("novo"),
        _historico_item("continuo"),
        _historico_item(
            "sumiu",
            observado=False,
        ),
        _historico_item(
            "ausente",
            observado=False,
        ),
        _historico_item(
            "voltou",
            reaparecimentos=1,
        ),
    ]

    resumo = _gerar(
        tmp_path,
        _estado(estados),
        _analise(historicos),
    )

    assert resumo.novas_no_ultimo_ciclo == 1
    assert resumo.continuaram_observadas == 1
    assert resumo.deixaram_de_ser_observadas == 1
    assert resumo.continuaram_ausentes == 1
    assert resumo.reapareceram_no_ultimo_ciclo == 1


def test_conta_reaparecimento_historico(
    tmp_path,
):
    resumo = _gerar(
        tmp_path,
        _estado(
            [
                _estado_item("a"),
                _estado_item("b"),
            ]
        ),
        _analise(
            [
                _historico_item(
                    "a",
                    reaparecimentos=2,
                ),
                _historico_item(
                    "b",
                    reaparecimentos=0,
                ),
            ]
        ),
    )

    assert resumo.com_reaparecimento_historico == 1


def test_duracao_atual_usa_episodio_quando_observado(
    tmp_path,
):
    resumo = _gerar(
        tmp_path,
        _estado([_estado_item("a")]),
        _analise(
            [
                _historico_item(
                    "a",
                    duracao=900.0,
                )
            ]
        ),
    )

    assert _por_codigo(resumo)["a"].duracao_estado_atual_segundos == 900.0


def test_duracao_atual_usa_ausencia_quando_ausente(
    tmp_path,
):
    resumo = _gerar(
        tmp_path,
        _estado(
            [
                _estado_item(
                    "a",
                    observado=False,
                    transicao="continua_nao_observado",
                )
            ]
        ),
        _analise(
            [
                _historico_item(
                    "a",
                    observado=False,
                    duracao=300.0,
                )
            ]
        ),
    )

    assert _por_codigo(resumo)["a"].duracao_estado_atual_segundos == 300.0


def test_inicio_historico_truncado_e_explicitado(
    tmp_path,
):
    resumo = _gerar(
        tmp_path,
        _estado([_estado_item("a")]),
        _analise(
            [
                _historico_item(
                    "a",
                    inicio_confirmado=False,
                )
            ]
        ),
    )

    assert _por_codigo(resumo)["a"].inicio_historico_truncado is True

    assert resumo.com_inicio_historico_truncado == 1


def test_ranking_observadas_usa_maior_duracao_atual(
    tmp_path,
):
    resumo = _gerar(
        tmp_path,
        _estado(
            [
                _estado_item("curta"),
                _estado_item("longa"),
            ]
        ),
        _analise(
            [
                _historico_item(
                    "curta",
                    duracao=100.0,
                ),
                _historico_item(
                    "longa",
                    duracao=500.0,
                ),
            ]
        ),
    )

    assert resumo.observadas_por_maior_duracao_atual == (
        "longa",
        "curta",
    )


def test_ranking_ausentes_usa_maior_duracao_atual(
    tmp_path,
):
    resumo = _gerar(
        tmp_path,
        _estado(
            [
                _estado_item(
                    "curta",
                    observado=False,
                    transicao="continua_nao_observado",
                ),
                _estado_item(
                    "longa",
                    observado=False,
                    transicao="continua_nao_observado",
                ),
            ]
        ),
        _analise(
            [
                _historico_item(
                    "curta",
                    observado=False,
                    duracao=100.0,
                ),
                _historico_item(
                    "longa",
                    observado=False,
                    duracao=500.0,
                ),
            ]
        ),
    )

    assert resumo.ausentes_por_maior_duracao_atual == (
        "longa",
        "curta",
    )


def test_node_divergente_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="Node IDs divergentes",
    ):
        _gerar(
            tmp_path,
            _estado(
                [_estado_item("a")],
                node_id="node-a",
            ),
            _analise(
                [_historico_item("a")],
                node_id="node-b",
            ),
        )


def test_mesmo_instante_com_offset_diferente_e_aceito(
    tmp_path,
):
    resumo = _gerar(
        tmp_path,
        _estado(
            [_estado_item("a")],
            referencia=("2026-09-10T16:10:00+00:00"),
        ),
        _analise(
            [_historico_item("a")],
            referencia=("2026-09-10T13:10:00-03:00"),
        ),
    )

    assert resumo.quantidade_interpretacoes == 1


def test_ciclo_divergente_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="ciclos diferentes",
    ):
        _gerar(
            tmp_path,
            _estado(
                [_estado_item("a")],
                referencia=("2026-09-10T16:10:00+00:00"),
            ),
            _analise(
                [_historico_item("a")],
                referencia=("2026-09-10T16:15:00+00:00"),
            ),
        )


def test_saida_atomica_e_sem_politica_operacional(
    tmp_path,
):
    resumo = _gerar(
        tmp_path,
        _estado([_estado_item("a")]),
        _analise([_historico_item("a")]),
    )

    caminho = tmp_path / "resumo.json"

    salvar_resumo_temporal_interpretacoes_node(
        resumo,
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
