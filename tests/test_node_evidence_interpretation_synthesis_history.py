import json

import pytest

from services.infra.node_evidence_interpretation_synthesis_history import (
    persistir_sintese_evidencias_interpretacoes_node,
)


def _sintese(
    referencia,
    *,
    node_id="node-v131",
    observado=True,
):
    return {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "cadencia_nominal_segundos": 300.0,
        "quantidade_interpretacoes": 1,
        "observadas_agora": (1 if observado else 0),
        "ausentes_agora": (0 if observado else 1),
        "com_reaparecimento_historico": [],
        "com_lacunas_evidencia_estimadas": [],
        "com_gaps_igual_ou_acima_2x_cadencia": [],
        "com_inicio_historico_truncado": [],
        "observadas_por_maior_duracao_atual": (["a"] if observado else []),
        "ausentes_por_maior_duracao_atual": ([] if observado else ["a"]),
        "por_menor_cobertura_evidencia": ["a"],
        "interpretacoes": [
            {
                "codigo": "a",
                "categoria": "teste",
                "sujeito": "a",
                "descricao": "Descricao a",
                "observado_agora": observado,
                "transicao_ultimo_ciclo": (
                    "continua_observado" if observado else "continua_nao_observado"
                ),
                "duracao_estado_atual_segundos": 300.0,
                "duracao_estado_atual_percentual_janela": 100.0,
                "quantidade_episodios_observados": 1,
                "reaparecimentos": 0,
                "quantidade_periodos_ausentes": (0 if observado else 1),
                "inicio_historico_truncado": False,
                "primeira_evidencia": ("2026-09-10T16:00:00+00:00"),
                "ultima_evidencia": referencia,
                "janela_evidencia_segundos": 300.0,
                "registros_com_evidencia": 2,
                "registros_esperados_desde_primeira_evidencia": 2,
                "registros_ausentes_estimados": 0,
                "razao_amostras_percentual": 100.0,
                "cobertura_evidencia_percentual": 100.0,
                "maior_gap_evidencia_segundos": 300.0,
                "gaps_igual_ou_acima_2x_cadencia": 0,
            }
        ],
    }


def _gravar(
    caminho,
    dados,
):
    caminho.write_text(
        json.dumps(dados),
        encoding="utf-8",
    )


def _persistir(
    tmp_path,
    sintese,
):
    caminho = tmp_path / "sintese.json"

    diretorio = tmp_path / "historico"

    _gravar(
        caminho,
        sintese,
    )

    return persistir_sintese_evidencias_interpretacoes_node(
        caminho,
        diretorio,
    )


def _linhas(
    caminho,
):
    return caminho.read_text(encoding="utf-8").splitlines()


def test_primeiro_registro_e_persistido(
    tmp_path,
):
    resultado = _persistir(
        tmp_path,
        _sintese("2026-09-10T16:05:00+00:00"),
    )

    assert resultado.registro_adicionado is True
    assert resultado.quantidade_registros_validos_node == 1
    assert resultado.caminho_historico.name == ("2026-09-10.jsonl")

    registros = [json.loads(linha) for linha in _linhas(resultado.caminho_historico)]

    assert len(registros) == 1

    assert registros[0]["referencia_temporal"] == "2026-09-10T16:05:00+00:00"


def test_mesmo_registro_e_idempotente(
    tmp_path,
):
    sintese = _sintese("2026-09-10T16:05:00+00:00")

    primeiro = _persistir(
        tmp_path,
        sintese,
    )

    segundo = _persistir(
        tmp_path,
        sintese,
    )

    assert primeiro.registro_adicionado is True
    assert segundo.registro_adicionado is False

    assert len(_linhas(segundo.caminho_historico)) == 1


def test_offset_equivalente_e_idempotente(
    tmp_path,
):
    _persistir(
        tmp_path,
        _sintese("2026-09-10T16:05:00+00:00"),
    )

    resultado = _persistir(
        tmp_path,
        _sintese("2026-09-10T13:05:00-03:00"),
    )

    assert resultado.registro_adicionado is False

    assert len(_linhas(resultado.caminho_historico)) == 1


def test_mesmo_instante_com_conteudo_diferente_e_rejeitado(
    tmp_path,
):
    _persistir(
        tmp_path,
        _sintese(
            "2026-09-10T16:05:00+00:00",
            observado=True,
        ),
    )

    with pytest.raises(
        ValueError,
        match="mesmo instante",
    ):
        _persistir(
            tmp_path,
            _sintese(
                "2026-09-10T16:05:00+00:00",
                observado=False,
            ),
        )


def test_registro_mais_antigo_e_rejeitado(
    tmp_path,
):
    _persistir(
        tmp_path,
        _sintese("2026-09-10T16:10:00+00:00"),
    )

    with pytest.raises(
        ValueError,
        match="mais antiga",
    ):
        _persistir(
            tmp_path,
            _sintese("2026-09-10T16:05:00+00:00"),
        )


def test_registro_mais_novo_e_adicionado(
    tmp_path,
):
    primeiro = _persistir(
        tmp_path,
        _sintese("2026-09-10T16:05:00+00:00"),
    )

    segundo = _persistir(
        tmp_path,
        _sintese("2026-09-10T16:10:00+00:00"),
    )

    assert segundo.registro_adicionado is True
    assert segundo.quantidade_registros_validos_node == 2

    assert len(_linhas(primeiro.caminho_historico)) == 2


def test_outro_node_nao_bloqueia_node_atual(
    tmp_path,
):
    _persistir(
        tmp_path,
        _sintese(
            "2026-09-10T17:00:00+00:00",
            node_id="node-outro",
        ),
    )

    resultado = _persistir(
        tmp_path,
        _sintese(
            "2026-09-10T16:00:00+00:00",
            node_id="node-atual",
        ),
    )

    assert resultado.registro_adicionado is True
    assert resultado.quantidade_registros_validos_node == 1


def test_linha_invalida_e_ignorada_e_preservada(
    tmp_path,
):
    diretorio = tmp_path / "historico"

    diretorio.mkdir(
        parents=True,
    )

    caminho_historico = diretorio / "2026-09-10.jsonl"

    caminho_historico.write_text(
        "linha-invalida\n",
        encoding="utf-8",
    )

    caminho_sintese = tmp_path / "sintese.json"

    _gravar(
        caminho_sintese,
        _sintese("2026-09-10T16:05:00+00:00"),
    )

    resultado = persistir_sintese_evidencias_interpretacoes_node(
        caminho_sintese,
        diretorio,
    )

    linhas = _linhas(resultado.caminho_historico)

    assert linhas[0] == "linha-invalida"
    assert len(linhas) == 2


def test_data_do_arquivo_usa_instante_utc(
    tmp_path,
):
    resultado = _persistir(
        tmp_path,
        _sintese("2026-09-10T23:30:00-03:00"),
    )

    assert resultado.caminho_historico.name == ("2026-09-11.jsonl")

    registro = json.loads(_linhas(resultado.caminho_historico)[0])

    assert registro["referencia_temporal"] == "2026-09-11T02:30:00+00:00"


def test_escrita_e_atomica(
    tmp_path,
):
    resultado = _persistir(
        tmp_path,
        _sintese("2026-09-10T16:05:00+00:00"),
    )

    temporario = resultado.caminho_historico.with_suffix(".jsonl.tmp")

    assert resultado.caminho_historico.exists()
    assert not temporario.exists()


def test_historico_nao_adiciona_politica_operacional(
    tmp_path,
):
    resultado = _persistir(
        tmp_path,
        _sintese("2026-09-10T16:05:00+00:00"),
    )

    texto = resultado.caminho_historico.read_text(encoding="utf-8")

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
