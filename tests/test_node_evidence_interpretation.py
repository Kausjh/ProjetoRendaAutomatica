import json

import pytest

from services.infra.node_evidence_interpretation import (
    interpretar_evidencias_node,
    salvar_interpretacao_evidencias_node,
)

NODE = "node-v119"
REF = "2026-09-10T16:00:00+00:00"


def _gravar(
    caminho,
    dados,
):
    caminho.write_text(
        json.dumps(dados),
        encoding="utf-8",
    )


def _base(
    tmp_path,
):
    codigo = "recurso_acima_baseline_e_subindo:" "cpu_percentual"

    resumo = {
        "versao_schema": 1,
        "node_id": NODE,
        "referencia_temporal": REF,
        "quantidade_sinais_conhecidos": 1,
        "quantidade_sinais_observados_agora": 1,
        "quantidade_supressoes_atuais": 0,
        "cadencia_nominal_segundos": 300.0,
        "qualidade_janela_recente": {
            "amostras_esperadas": 13,
            "amostras_observadas": 13,
            "timestamps_distintos": 13,
            "timestamps_repetidos": 0,
            "amostras_excedentes": 0,
            "razao_amostras_percentual": 100.0,
            "cobertura_normalizada_percentual": 100.0,
        },
        "qualidade_janela_baseline": {
            "amostras_esperadas": 72,
            "amostras_observadas": 74,
            "timestamps_distintos": 74,
            "timestamps_repetidos": 0,
            "amostras_excedentes": 2,
            "razao_amostras_percentual": 102.777777,
            "cobertura_normalizada_percentual": 100.0,
        },
        "sinais": [],
        "supressoes": [],
    }

    qualidade = {
        "versao_schema": 1,
        "node_id": NODE,
        "referencia_temporal": REF,
        "cobertura_referencia_percentual": 80.0,
        "janela_recente_cobertura_percentual": 100.0,
        "janela_baseline_cobertura_percentual": 100.0,
        "janela_recente_amostras_esperadas": 13,
        "janela_recente_amostras_observadas": 13,
        "janela_baseline_amostras_esperadas": 72,
        "janela_baseline_amostras_observadas": 74,
        "janela_recente_gaps_2x_cadencia": 0,
        "janela_baseline_gaps_2x_cadencia": 0,
        "janela_recente_timestamps_repetidos": 0,
        "janela_baseline_timestamps_repetidos": 0,
        "quantidade_sinais": 1,
        "quantidade_supressoes": 0,
        "sinais": [
            {
                "codigo": codigo,
                "observado_agora": True,
                "quantidade_episodios": 2,
                "reaparecimentos": 1,
                "inicio_historico_truncado": True,
                "episodio_atual_aberto": True,
                "duracao_episodio_atual_segundos": 300.0,
                "maior_duracao_acompanhada_segundos": 900.0,
                "qualidade_relacionada_tipo": "metrica",
                "qualidade_relacionada_nome": "cpu_percentual",
                "cobertura_recente_percentual": 100.0,
                "cobertura_baseline_percentual": 75.0,
                "cobertura_referencia_percentual": 80.0,
                "cobertura_recente_atinge_referencia": True,
                "cobertura_baseline_atinge_referencia": False,
            }
        ],
        "supressoes": [],
    }

    caminhos = {
        "resumo": tmp_path / "resumo.json",
        "qualidade": tmp_path / "qualidade.json",
    }

    _gravar(
        caminhos["resumo"],
        resumo,
    )

    _gravar(
        caminhos["qualidade"],
        qualidade,
    )

    return (
        caminhos,
        resumo,
        qualidade,
        codigo,
    )


def _interpretar(
    caminhos,
):
    return interpretar_evidencias_node(
        caminho_resumo=caminhos["resumo"],
        caminho_qualidade_temporal=caminhos["qualidade"],
    )


def _codigos(
    interpretacao,
):
    return {item.codigo for item in interpretacao.observacoes}


def test_janelas_geram_comparacao_de_cobertura(
    tmp_path,
):
    caminhos, _, _, _ = _base(tmp_path)

    codigos = _codigos(_interpretar(caminhos))

    assert "janela_recente:" "cobertura_atinge_referencia" in codigos

    assert "janela_baseline:" "cobertura_atinge_referencia" in codigos


def test_amostragem_acima_do_previsto_e_explicita(
    tmp_path,
):
    caminhos, _, _, _ = _base(tmp_path)

    codigos = _codigos(_interpretar(caminhos))

    assert "janela_baseline:" "amostras_observadas_acima_esperadas" in codigos


def test_gap_e_timestamp_repetido_sao_observacoes(
    tmp_path,
):
    (
        caminhos,
        _,
        qualidade,
        _,
    ) = _base(tmp_path)

    qualidade["janela_recente_gaps_2x_cadencia"] = 2

    qualidade["janela_baseline_timestamps_repetidos"] = 1

    _gravar(
        caminhos["qualidade"],
        qualidade,
    )

    codigos = _codigos(_interpretar(caminhos))

    assert "janela_recente:" "gap_2x_cadencia_observado" in codigos

    assert "janela_baseline:" "timestamp_repetido_observado" in codigos


def test_sinal_atual_e_recorrencia_sao_explicitos(
    tmp_path,
):
    (
        caminhos,
        _,
        _,
        codigo,
    ) = _base(tmp_path)

    codigos = _codigos(_interpretar(caminhos))

    assert "sinal_observado_agora:" + codigo in codigos

    assert "recorrencia_observada:" + codigo in codigos


def test_inicio_truncado_e_episodio_aberto_sao_explicitos(
    tmp_path,
):
    (
        caminhos,
        _,
        _,
        codigo,
    ) = _base(tmp_path)

    codigos = _codigos(_interpretar(caminhos))

    assert "inicio_historico_truncado:" + codigo in codigos

    assert "episodio_aberto_no_fim_da_janela:" + codigo in codigos


def test_cobertura_do_sinal_preserva_duas_janelas(
    tmp_path,
):
    (
        caminhos,
        _,
        _,
        codigo,
    ) = _base(tmp_path)

    codigos = _codigos(_interpretar(caminhos))

    assert "cobertura_recente:" "atinge_referencia:" + codigo in codigos

    assert "cobertura_baseline:" "nao_atinge_referencia:" + codigo in codigos


def test_supressao_e_preservada_com_evidencia(
    tmp_path,
):
    (
        caminhos,
        _,
        qualidade,
        _,
    ) = _base(tmp_path)

    codigo = "tendencia_recurso:" "memoria_processos_projeto_bytes"

    qualidade["supressoes"] = [
        {
            "codigo": codigo,
            "motivo": "Evidencia insuficiente.",
            "qualidade_relacionada_tipo": "metrica",
            "qualidade_relacionada_nome": ("memoria_processos_projeto_bytes"),
            "cobertura_recente_percentual": 100.0,
            "cobertura_baseline_percentual": 62.0,
            "cobertura_referencia_percentual": 80.0,
            "cobertura_recente_atinge_referencia": True,
            "cobertura_baseline_atinge_referencia": False,
        }
    ]

    qualidade["quantidade_supressoes"] = 1

    _gravar(
        caminhos["qualidade"],
        qualidade,
    )

    interpretacao = _interpretar(caminhos)

    encontrados = [
        item
        for item in interpretacao.observacoes
        if item.codigo == ("supressao_observada:" + codigo)
    ]

    assert len(encontrados) == 1

    assert encontrados[0].dados["cobertura_baseline_percentual"] == 62.0


def test_node_diferente_e_rejeitado(
    tmp_path,
):
    (
        caminhos,
        _,
        qualidade,
        _,
    ) = _base(tmp_path)

    qualidade["node_id"] = "node-outro"

    _gravar(
        caminhos["qualidade"],
        qualidade,
    )

    with pytest.raises(
        ValueError,
        match="nodes diferentes",
    ):
        _interpretar(caminhos)


def test_mesmo_instante_com_offset_e_aceito(
    tmp_path,
):
    (
        caminhos,
        _,
        qualidade,
        _,
    ) = _base(tmp_path)

    qualidade["referencia_temporal"] = "2026-09-10T13:00:00-03:00"

    _gravar(
        caminhos["qualidade"],
        qualidade,
    )

    interpretacao = _interpretar(caminhos)

    assert interpretacao.node_id == NODE


def test_ciclo_diferente_e_rejeitado(
    tmp_path,
):
    (
        caminhos,
        _,
        qualidade,
        _,
    ) = _base(tmp_path)

    qualidade["referencia_temporal"] = "2026-09-10T16:05:00+00:00"

    _gravar(
        caminhos["qualidade"],
        qualidade,
    )

    with pytest.raises(
        ValueError,
        match="ciclos temporais diferentes",
    ):
        _interpretar(caminhos)


def test_saida_atomica_e_sem_politica_operacional(
    tmp_path,
):
    caminhos, _, _, _ = _base(tmp_path)

    interpretacao = _interpretar(caminhos)

    caminho = tmp_path / "interpretacao.json"

    salvar_interpretacao_evidencias_node(
        interpretacao,
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
