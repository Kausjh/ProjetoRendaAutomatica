import json

import pytest

from services.infra.node_evidence_interpretation_history_analysis import (
    analisar_historico_interpretacoes_node,
    salvar_analise_historico_interpretacoes_node,
)


def _item(
    codigo,
    observado,
    transicao,
):
    return {
        "codigo": codigo,
        "categoria": "teste",
        "sujeito": codigo,
        "descricao": (f"Descricao {codigo}"),
        "primeira_observacao": ("2026-09-10T16:00:00+00:00"),
        "inicio_sequencia_atual": ("2026-09-10T16:00:00+00:00"),
        "ultima_observacao": ("2026-09-10T16:00:00+00:00"),
        "observado_agora": observado,
        "observacoes_consecutivas": (1 if observado else 0),
        "observacoes_totais": 1,
        "ciclos_ausente_consecutivos": (0 if observado else 1),
        "deixou_de_ser_observado_em": (None if observado else "2026-09-10T16:05:00+00:00"),
        "transicao_ultimo_ciclo": transicao,
        "dados_mais_recentes": {},
        "fontes_mais_recentes": ["fonte.json"],
    }


def _registro(
    referencia,
    observacoes,
    *,
    node_id="node-v123",
):
    return {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "quantidade_observacoes_conhecidas": len(observacoes),
        "quantidade_observadas_agora": sum(1 for item in observacoes if item["observado_agora"]),
        "observacoes": observacoes,
    }


def _gravar(
    diretorio,
    registros,
):
    diretorio.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho = diretorio / "2026-09-10.jsonl"

    caminho.write_text(
        "".join(json.dumps(registro) + "\n" for registro in registros),
        encoding="utf-8",
    )


def _analisar(
    tmp_path,
    registros,
):
    diretorio = tmp_path / "historico"

    _gravar(
        diretorio,
        registros,
    )

    return analisar_historico_interpretacoes_node(diretorio)


def _por_codigo(
    analise,
):
    return {item.codigo: item for item in analise.interpretacoes}


def test_observacao_continua_forma_um_episodio_aberto(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _registro(
                "2026-09-10T16:00:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "novo",
                    )
                ],
            ),
            _registro(
                "2026-09-10T16:05:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "continua_observado",
                    )
                ],
            ),
        ],
    )

    item = _por_codigo(analise)["a"]

    assert item.observado_agora is True
    assert item.quantidade_episodios_observados == 1
    assert item.episodio_atual_aberto is True
    assert item.duracao_episodio_atual_segundos == 300.0


def test_false_fecha_episodio_e_abre_ausencia(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _registro(
                "2026-09-10T16:00:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "novo",
                    )
                ],
            ),
            _registro(
                "2026-09-10T16:05:00+00:00",
                [
                    _item(
                        "a",
                        False,
                        "deixou_de_ser_observado",
                    )
                ],
            ),
            _registro(
                "2026-09-10T16:10:00+00:00",
                [
                    _item(
                        "a",
                        False,
                        "continua_nao_observado",
                    )
                ],
            ),
        ],
    )

    item = _por_codigo(analise)["a"]

    assert item.observado_agora is False
    assert item.quantidade_episodios_observados == 1
    assert item.quantidade_periodos_ausentes == 1
    assert item.periodo_ausencia_atual_aberto is True
    assert item.duracao_ausencia_atual_segundos == 300.0


def test_reaparecimento_cria_segundo_episodio(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _registro(
                "2026-09-10T16:00:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "novo",
                    )
                ],
            ),
            _registro(
                "2026-09-10T16:05:00+00:00",
                [
                    _item(
                        "a",
                        False,
                        "deixou_de_ser_observado",
                    )
                ],
            ),
            _registro(
                "2026-09-10T16:10:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "reapareceu",
                    )
                ],
            ),
        ],
    )

    item = _por_codigo(analise)["a"]

    assert item.quantidade_episodios_observados == 2
    assert item.reaparecimentos == 1
    assert item.quantidade_periodos_ausentes == 1
    assert item.observado_agora is True


def test_primeiro_continua_observado_tem_inicio_nao_confirmado(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _registro(
                "2026-09-10T16:05:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "continua_observado",
                    )
                ],
            ),
            _registro(
                "2026-09-10T16:10:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "continua_observado",
                    )
                ],
            ),
        ],
    )

    episodio = _por_codigo(analise)["a"].episodios_observados[0]

    assert episodio.inicio_confirmado is False
    assert episodio.fim_confirmado is False


def test_primeiro_continua_ausente_tem_inicio_nao_confirmado(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _registro(
                "2026-09-10T16:05:00+00:00",
                [
                    _item(
                        "a",
                        False,
                        "continua_nao_observado",
                    )
                ],
            ),
            _registro(
                "2026-09-10T16:10:00+00:00",
                [
                    _item(
                        "a",
                        False,
                        "continua_nao_observado",
                    )
                ],
            ),
        ],
    )

    ausencia = _por_codigo(analise)["a"].periodos_ausentes[0]

    assert ausencia.inicio_confirmado is False
    assert ausencia.fim_confirmado is False


def test_observacao_ausente_de_um_snapshot_nao_vira_false(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _registro(
                "2026-09-10T16:00:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "novo",
                    )
                ],
            ),
            _registro(
                "2026-09-10T16:05:00+00:00",
                [],
            ),
            _registro(
                "2026-09-10T16:10:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "continua_observado",
                    )
                ],
            ),
        ],
    )

    item = _por_codigo(analise)["a"]

    assert item.quantidade_episodios_observados == 1
    assert item.quantidade_periodos_ausentes == 0
    assert item.observacoes_explicitas == 2
    assert item.duracao_episodio_atual_segundos == 600.0


def test_registros_fora_de_ordem_sao_ordenados(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _registro(
                "2026-09-10T16:05:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "continua_observado",
                    )
                ],
            ),
            _registro(
                "2026-09-10T16:00:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "novo",
                    )
                ],
            ),
        ],
    )

    assert analise.inicio_periodo == "2026-09-10T16:00:00+00:00"

    assert analise.fim_periodo == "2026-09-10T16:05:00+00:00"


def test_duplicate_equivalente_no_mesmo_instante_e_ignorado(
    tmp_path,
):
    primeiro = _registro(
        "2026-09-10T16:00:00+00:00",
        [
            _item(
                "a",
                True,
                "novo",
            )
        ],
    )

    segundo = dict(primeiro)

    segundo["referencia_temporal"] = "2026-09-10T13:00:00-03:00"

    analise = _analisar(
        tmp_path,
        [
            primeiro,
            segundo,
        ],
    )

    assert analise.quantidade_registros == 1

    assert _por_codigo(analise)["a"].observacoes_explicitas == 1


def test_mesmo_instante_com_estados_diferentes_e_rejeitado(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="mesmo instante",
    ):
        _analisar(
            tmp_path,
            [
                _registro(
                    "2026-09-10T16:00:00+00:00",
                    [
                        _item(
                            "a",
                            True,
                            "novo",
                        )
                    ],
                ),
                _registro(
                    "2026-09-10T16:00:00+00:00",
                    [
                        _item(
                            "a",
                            False,
                            "deixou_de_ser_observado",
                        )
                    ],
                ),
            ],
        )


def test_apenas_node_mais_recente_e_analisado(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _registro(
                "2026-09-10T15:55:00+00:00",
                [
                    _item(
                        "antiga",
                        True,
                        "novo",
                    )
                ],
                node_id="node-antigo",
            ),
            _registro(
                "2026-09-10T16:00:00+00:00",
                [
                    _item(
                        "nova",
                        True,
                        "novo",
                    )
                ],
                node_id="node-novo",
            ),
        ],
    )

    assert analise.node_id == "node-novo"

    assert {item.codigo for item in analise.interpretacoes} == {"nova"}


def test_saida_atomica_e_sem_politica_operacional(
    tmp_path,
):
    analise = _analisar(
        tmp_path,
        [
            _registro(
                "2026-09-10T16:00:00+00:00",
                [
                    _item(
                        "a",
                        True,
                        "novo",
                    )
                ],
            )
        ],
    )

    caminho = tmp_path / "analise.json"

    salvar_analise_historico_interpretacoes_node(
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
