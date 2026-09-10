import json

import pytest

from services.infra.node_evidence_summary import (
    gerar_resumo_evidencias_node,
    salvar_resumo_evidencias_node,
)

REF = "2026-09-10T13:30:00+00:00"
NODE = "node-teste"


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
    *,
    node_id=NODE,
    referencia=REF,
):
    sinais = {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "servicos_continuos": [],
        "dependencias_persistentes": [],
        "workloads_intermitentes": [],
        "sinais": [],
        "supressoes": [],
    }

    estado = {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "sinais": [
            {
                "codigo": ("recurso_acima_baseline_e_subindo:" "cpu_percentual"),
                "origem": "tendencia",
                "titulo": "CPU",
                "primeira_observacao": referencia,
                "inicio_sequencia_atual": referencia,
                "ultima_observacao": referencia,
                "observado_agora": True,
                "observacoes_consecutivas": 2,
                "observacoes_totais": 4,
                "ciclos_ausente_consecutivos": 0,
                "deixou_de_ser_observado_em": None,
                "transicao_ultimo_ciclo": ("continua_observado"),
                "evidencias_mais_recentes": {
                    "valor": 70.0,
                },
            }
        ],
    }

    historico = {
        "versao_schema": 1,
        "node_id": node_id,
        "inicio_periodo": ("2026-09-10T13:00:00+00:00"),
        "fim_periodo": referencia,
        "quantidade_amostras": 7,
        "linhas_invalidas_ignoradas": 0,
        "amostras_duplicadas_ignoradas": 0,
        "sinais": [
            {
                "codigo": ("recurso_acima_baseline_e_subindo:" "cpu_percentual"),
                "origem": "tendencia",
                "titulo": "CPU",
                "observado_agora": True,
                "quantidade_episodios": 2,
                "reaparecimentos": 1,
                "duracao_episodio_atual_segundos": 300.0,
                "maior_duracao_acompanhada_segundos": 900.0,
                "media_duracao_episodios_encerrados_segundos": 600.0,
                "ultimo_intervalo_entre_episodios_segundos": 1200.0,
                "media_intervalo_entre_episodios_segundos": 1200.0,
                "episodios": [],
            }
        ],
    }

    qualidade = {
        "versao_schema": 1,
        "node_id": node_id,
        "referencia_temporal": referencia,
        "cadencia_nominal_segundos": 300.0,
        "janela_recente": {
            "nome": "recente",
            "amostras_esperadas": 13,
            "amostras_observadas": 13,
            "razao_amostras_percentual": 100.0,
        },
        "janela_baseline": {
            "nome": "baseline",
            "amostras_esperadas": 72,
            "amostras_observadas": 72,
            "razao_amostras_percentual": 100.0,
        },
        "metricas": [
            {
                "nome": "cpu_percentual",
                "amostras_com_valor_recente": 13,
                "amostras_com_valor_baseline": 72,
                "percentual_presenca_recente": 100.0,
                "percentual_presenca_baseline": 100.0,
                "comparacao_disponivel": True,
                "inclinacao_recente_disponivel": True,
            }
        ],
        "servicos": [
            {
                "nome": "runtime",
                "amostras_observadas_recente": 13,
                "amostras_observadas_baseline": 72,
                "percentual_presenca_recente": 100.0,
                "percentual_presenca_baseline": 100.0,
                "memoria_rss_bytes": {},
            }
        ],
    }

    caminhos = {
        "sinais": tmp_path / "sinais.json",
        "estado": tmp_path / "estado.json",
        "historico": tmp_path / "historico.json",
        "qualidade": tmp_path / "qualidade.json",
    }

    _gravar(
        caminhos["sinais"],
        sinais,
    )

    _gravar(
        caminhos["estado"],
        estado,
    )

    _gravar(
        caminhos["historico"],
        historico,
    )

    _gravar(
        caminhos["qualidade"],
        qualidade,
    )

    return (
        caminhos,
        sinais,
        estado,
        historico,
        qualidade,
    )


def _gerar(
    caminhos,
):
    return gerar_resumo_evidencias_node(
        caminho_sinais=caminhos["sinais"],
        caminho_estado_temporal=caminhos["estado"],
        caminho_historico_sinais=caminhos["historico"],
        caminho_qualidade=caminhos["qualidade"],
    )


def test_estado_temporal_define_universo_de_sinais(
    tmp_path,
):
    (
        caminhos,
        _,
        _,
        _,
        _,
    ) = _base(tmp_path)

    resumo = _gerar(caminhos)

    assert resumo.quantidade_sinais_conhecidos == 1
    assert resumo.quantidade_sinais_observados_agora == 1
    assert len(resumo.sinais) == 1


def test_historico_enriquece_sinal(
    tmp_path,
):
    (
        caminhos,
        _,
        _,
        _,
        _,
    ) = _base(tmp_path)

    sinal = _gerar(caminhos).sinais[0]

    assert sinal.historico_disponivel is True
    assert sinal.quantidade_episodios == 2
    assert sinal.reaparecimentos == 1

    assert sinal.maior_duracao_acompanhada_segundos == 900.0


def test_metrica_de_qualidade_e_associada_ao_sinal(
    tmp_path,
):
    (
        caminhos,
        _,
        _,
        _,
        _,
    ) = _base(tmp_path)

    sinal = _gerar(caminhos).sinais[0]

    assert sinal.qualidade_relacionada is not None

    assert sinal.qualidade_relacionada["tipo"] == "metrica"

    assert sinal.qualidade_relacionada["nome"] == "cpu_percentual"


def test_evidencia_do_ciclo_atual_e_preservada(
    tmp_path,
):
    (
        caminhos,
        sinais,
        _,
        _,
        _,
    ) = _base(tmp_path)

    sinais["sinais"] = [
        {
            "codigo": ("recurso_acima_baseline_e_subindo:" "cpu_percentual"),
            "origem": "tendencia",
            "titulo": "CPU",
            "descricao": "teste",
            "evidencias": {
                "atual": 80.0,
            },
        }
    ]

    _gravar(
        caminhos["sinais"],
        sinais,
    )

    sinal = _gerar(caminhos).sinais[0]

    assert sinal.evidencia_ciclo_atual == {
        "atual": 80.0,
    }


def test_supressao_e_associada_a_qualidade(
    tmp_path,
):
    (
        caminhos,
        sinais,
        _,
        _,
        qualidade,
    ) = _base(tmp_path)

    qualidade["metricas"].append(
        {
            "nome": ("memoria_processos_projeto_bytes"),
            "amostras_com_valor_recente": 13,
            "amostras_com_valor_baseline": 20,
            "percentual_presenca_recente": 100.0,
            "percentual_presenca_baseline": 30.0,
            "comparacao_disponivel": True,
            "inclinacao_recente_disponivel": True,
        }
    )

    sinais["supressoes"] = [
        {
            "codigo": ("tendencia_recurso:" "memoria_processos_projeto_bytes"),
            "motivo": "Evidencia insuficiente.",
            "evidencias": {
                "cobertura_minima_percentual": 80.0,
            },
        }
    ]

    _gravar(
        caminhos["sinais"],
        sinais,
    )

    _gravar(
        caminhos["qualidade"],
        qualidade,
    )

    resumo = _gerar(caminhos)

    assert resumo.quantidade_supressoes_atuais == 1

    supressao = resumo.supressoes[0]

    assert supressao.qualidade_relacionada["tipo"] == "metrica"

    assert supressao.qualidade_relacionada["nome"] == "memoria_processos_projeto_bytes"


def test_janela_recente_e_associada_a_sinal_global(
    tmp_path,
):
    (
        caminhos,
        _,
        estado,
        historico,
        _,
    ) = _base(tmp_path)

    codigo = "cobertura_coleta_recente_incompleta"

    estado["sinais"] = [
        {
            "codigo": codigo,
            "origem": "qualidade",
            "titulo": "Cobertura",
            "primeira_observacao": REF,
            "inicio_sequencia_atual": REF,
            "ultima_observacao": REF,
            "observado_agora": True,
            "observacoes_consecutivas": 1,
            "observacoes_totais": 1,
            "ciclos_ausente_consecutivos": 0,
            "deixou_de_ser_observado_em": None,
            "transicao_ultimo_ciclo": "novo",
            "evidencias_mais_recentes": {},
        }
    ]

    historico["sinais"] = []

    _gravar(
        caminhos["estado"],
        estado,
    )

    _gravar(
        caminhos["historico"],
        historico,
    )

    sinal = _gerar(caminhos).sinais[0]

    assert sinal.qualidade_relacionada is not None

    assert sinal.qualidade_relacionada["tipo"] == "janela_recente"


def test_node_diferente_e_rejeitado(
    tmp_path,
):
    (
        caminhos,
        _,
        _,
        historico,
        _,
    ) = _base(tmp_path)

    historico["node_id"] = "node-outro"

    _gravar(
        caminhos["historico"],
        historico,
    )

    with pytest.raises(
        ValueError,
        match="nodes diferentes",
    ):
        _gerar(caminhos)


def test_ciclo_temporal_diferente_e_rejeitado(
    tmp_path,
):
    (
        caminhos,
        _,
        _,
        _,
        qualidade,
    ) = _base(tmp_path)

    qualidade["referencia_temporal"] = "2026-09-10T13:35:00+00:00"

    _gravar(
        caminhos["qualidade"],
        qualidade,
    )

    with pytest.raises(
        ValueError,
        match="ciclos temporais diferentes",
    ):
        _gerar(caminhos)


def test_saida_atomica_e_sem_politica_operacional(
    tmp_path,
):
    (
        caminhos,
        _,
        _,
        _,
        _,
    ) = _base(tmp_path)

    resumo = _gerar(caminhos)

    caminho = tmp_path / "resumo.json"

    salvar_resumo_evidencias_node(
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
    ):
        assert termo not in texto
