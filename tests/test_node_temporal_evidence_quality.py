import json

import pytest

from services.infra.node_temporal_evidence_quality import (
    analisar_qualidade_temporal_evidencia_node,
    salvar_qualidade_temporal_evidencia_node,
)

NODE = "node-v116"
REF = "2026-09-10T14:00:00+00:00"


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
            "nome": "recente",
            "amostras_esperadas": 13,
            "amostras_observadas": 12,
            "razao_amostras_percentual": 92.307692,
            "gaps_igual_ou_acima_2x_cadencia": 1,
            "timestamps_repetidos": 0,
        },
        "qualidade_janela_baseline": {
            "nome": "baseline",
            "amostras_esperadas": 72,
            "amostras_observadas": 70,
            "razao_amostras_percentual": 97.222222,
            "gaps_igual_ou_acima_2x_cadencia": 0,
            "timestamps_repetidos": 1,
        },
        "sinais": [
            {
                "codigo": codigo,
                "origem": "tendencia",
                "titulo": "CPU",
                "observado_agora": True,
                "transicao_ultimo_ciclo": ("continua_observado"),
                "primeira_observacao": REF,
                "inicio_sequencia_atual": REF,
                "ultima_observacao": REF,
                "observacoes_consecutivas": 2,
                "observacoes_totais": 4,
                "ciclos_ausente_consecutivos": 0,
                "deixou_de_ser_observado_em": None,
                "evidencia_ciclo_atual": {},
                "evidencias_mais_recentes": {},
                "historico_disponivel": True,
                "quantidade_episodios": 2,
                "reaparecimentos": 1,
                "duracao_episodio_atual_segundos": 300.0,
                "maior_duracao_acompanhada_segundos": 900.0,
                "media_duracao_episodios_encerrados_segundos": 600.0,
                "ultimo_intervalo_entre_episodios_segundos": 1200.0,
                "media_intervalo_entre_episodios_segundos": 1200.0,
                "qualidade_relacionada": {
                    "tipo": "metrica",
                    "nome": "cpu_percentual",
                    "dados": {
                        "nome": "cpu_percentual",
                        "amostras_com_valor_recente": 13,
                        "amostras_com_valor_baseline": 72,
                        "percentual_presenca_recente": 100.0,
                        "percentual_presenca_baseline": 75.0,
                        "comparacao_disponivel": True,
                        "inclinacao_recente_disponivel": True,
                    },
                },
            }
        ],
        "supressoes": [],
    }

    historico = {
        "versao_schema": 1,
        "node_id": NODE,
        "inicio_periodo": ("2026-09-10T13:00:00+00:00"),
        "fim_periodo": REF,
        "quantidade_amostras": 13,
        "linhas_invalidas_ignoradas": 0,
        "amostras_duplicadas_ignoradas": 0,
        "sinais": [
            {
                "codigo": codigo,
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
                "episodios": [
                    {
                        "inicio_em": ("2026-09-10T13:00:00+00:00"),
                        "fim_detectado_em": ("2026-09-10T13:10:00+00:00"),
                        "inicio_confirmado": False,
                        "aberto_no_fim_da_janela": False,
                        "observacoes_ativas": 3,
                        "duracao_acompanhada_segundos": 600.0,
                    },
                    {
                        "inicio_em": ("2026-09-10T13:55:00+00:00"),
                        "fim_detectado_em": None,
                        "inicio_confirmado": True,
                        "aberto_no_fim_da_janela": True,
                        "observacoes_ativas": 2,
                        "duracao_acompanhada_segundos": 300.0,
                    },
                ],
            }
        ],
    }

    caminhos = {
        "resumo": (tmp_path / "resumo.json"),
        "historico": (tmp_path / "historico.json"),
    }

    _gravar(
        caminhos["resumo"],
        resumo,
    )

    _gravar(
        caminhos["historico"],
        historico,
    )

    return (
        caminhos,
        resumo,
        historico,
    )


def _analisar(
    caminhos,
):
    return analisar_qualidade_temporal_evidencia_node(
        caminho_resumo=(caminhos["resumo"]),
        caminho_historico_sinais=(caminhos["historico"]),
    )


def test_cobertura_de_metrica_e_preservada(
    tmp_path,
):
    caminhos, _, _ = _base(tmp_path)

    sinal = _analisar(caminhos).sinais[0]

    assert sinal.cobertura_recente_percentual == 100.0
    assert sinal.cobertura_baseline_percentual == 75.0

    assert sinal.cobertura_recente_atinge_referencia is True

    assert sinal.cobertura_baseline_atinge_referencia is False


def test_inicio_historico_truncado_e_detectado(
    tmp_path,
):
    caminhos, _, _ = _base(tmp_path)

    sinal = _analisar(caminhos).sinais[0]

    assert sinal.inicio_historico_truncado is True


def test_episodio_atual_aberto_e_detectado(
    tmp_path,
):
    caminhos, _, _ = _base(tmp_path)

    sinal = _analisar(caminhos).sinais[0]

    assert sinal.episodio_atual_aberto is True

    assert sinal.duracao_episodio_atual_segundos == 300.0


def test_recorrencia_e_preservada(
    tmp_path,
):
    caminhos, _, _ = _base(tmp_path)

    sinal = _analisar(caminhos).sinais[0]

    assert sinal.quantidade_episodios == 2
    assert sinal.reaparecimentos == 1


def test_janelas_preservam_gaps_e_repeticoes(
    tmp_path,
):
    caminhos, _, _ = _base(tmp_path)

    analise = _analisar(caminhos)

    assert analise.janela_recente_gaps_2x_cadencia == 1

    assert analise.janela_baseline_gaps_2x_cadencia == 0

    assert analise.janela_recente_timestamps_repetidos == 0

    assert analise.janela_baseline_timestamps_repetidos == 1


def test_sinal_global_usa_cobertura_da_janela_recente(
    tmp_path,
):
    caminhos, resumo, historico = _base(tmp_path)

    codigo = "cobertura_coleta_recente_incompleta"

    resumo["sinais"] = [
        {
            "codigo": codigo,
            "observado_agora": True,
            "quantidade_episodios": 1,
            "reaparecimentos": 0,
            "duracao_episodio_atual_segundos": 300.0,
            "maior_duracao_acompanhada_segundos": 300.0,
            "qualidade_relacionada": {
                "tipo": "janela_recente",
                "nome": "janela_recente",
                "dados": {
                    "razao_amostras_percentual": 70.0,
                },
            },
        }
    ]

    historico["sinais"] = [
        {
            "codigo": codigo,
            "episodios": [
                {
                    "inicio_confirmado": True,
                    "aberto_no_fim_da_janela": True,
                }
            ],
        }
    ]

    _gravar(
        caminhos["resumo"],
        resumo,
    )

    _gravar(
        caminhos["historico"],
        historico,
    )

    sinal = _analisar(caminhos).sinais[0]

    assert sinal.cobertura_recente_percentual == 70.0
    assert sinal.cobertura_baseline_percentual is None

    assert sinal.cobertura_recente_atinge_referencia is False

    assert sinal.cobertura_baseline_atinge_referencia is None


def test_supressao_preserva_referencia_e_cobertura(
    tmp_path,
):
    caminhos, resumo, _ = _base(tmp_path)

    resumo["supressoes"] = [
        {
            "codigo": ("tendencia_recurso:" "memoria_processos_projeto_bytes"),
            "motivo": "Evidencia insuficiente.",
            "evidencias": {
                "cobertura_minima_percentual": 80.0,
            },
            "qualidade_relacionada": {
                "tipo": "metrica",
                "nome": ("memoria_processos_projeto_bytes"),
                "dados": {
                    "percentual_presenca_recente": 100.0,
                    "percentual_presenca_baseline": 38.0,
                },
            },
        }
    ]

    _gravar(
        caminhos["resumo"],
        resumo,
    )

    supressao = _analisar(caminhos).supressoes[0]

    assert supressao.cobertura_referencia_percentual == 80.0

    assert supressao.cobertura_recente_atinge_referencia is True

    assert supressao.cobertura_baseline_atinge_referencia is False


def test_node_diferente_e_rejeitado(
    tmp_path,
):
    caminhos, _, historico = _base(tmp_path)

    historico["node_id"] = "node-outro"

    _gravar(
        caminhos["historico"],
        historico,
    )

    with pytest.raises(
        ValueError,
        match="nodes diferentes",
    ):
        _analisar(caminhos)


def test_mesmo_instante_com_offset_e_aceito(
    tmp_path,
):
    caminhos, _, historico = _base(tmp_path)

    historico["fim_periodo"] = "2026-09-10T11:00:00-03:00"

    _gravar(
        caminhos["historico"],
        historico,
    )

    analise = _analisar(caminhos)

    assert analise.node_id == NODE


def test_saida_atomica_e_sem_politica_operacional(
    tmp_path,
):
    caminhos, _, _ = _base(tmp_path)

    analise = _analisar(caminhos)

    caminho = tmp_path / "qualidade_temporal.json"

    salvar_qualidade_temporal_evidencia_node(
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


def test_cobertura_de_janela_prefere_valor_normalizado(
    tmp_path,
):
    caminhos, resumo, historico = _base(tmp_path)

    resumo["qualidade_janela_recente"]["razao_amostras_percentual"] = 110.0

    resumo["qualidade_janela_recente"]["cobertura_normalizada_percentual"] = 100.0

    resumo["qualidade_janela_baseline"]["razao_amostras_percentual"] = 102.0

    resumo["qualidade_janela_baseline"]["cobertura_normalizada_percentual"] = 100.0

    _gravar(
        caminhos["resumo"],
        resumo,
    )

    _gravar(
        caminhos["historico"],
        historico,
    )

    analise = _analisar(caminhos)

    assert analise.janela_recente_cobertura_percentual == 100.0

    assert analise.janela_baseline_cobertura_percentual == 100.0


def test_sinal_de_janela_prefere_cobertura_normalizada(
    tmp_path,
):
    caminhos, resumo, historico = _base(tmp_path)

    codigo = "cobertura_coleta_recente_incompleta"

    resumo["sinais"] = [
        {
            "codigo": codigo,
            "observado_agora": True,
            "quantidade_episodios": 1,
            "reaparecimentos": 0,
            "duracao_episodio_atual_segundos": 300.0,
            "maior_duracao_acompanhada_segundos": 300.0,
            "qualidade_relacionada": {
                "tipo": "janela_recente",
                "nome": "janela_recente",
                "dados": {
                    "razao_amostras_percentual": 120.0,
                    "cobertura_normalizada_percentual": 100.0,
                },
            },
        }
    ]

    historico["sinais"] = [
        {
            "codigo": codigo,
            "episodios": [
                {
                    "inicio_confirmado": True,
                    "aberto_no_fim_da_janela": True,
                }
            ],
        }
    ]

    _gravar(
        caminhos["resumo"],
        resumo,
    )

    _gravar(
        caminhos["historico"],
        historico,
    )

    sinal = _analisar(caminhos).sinais[0]

    assert sinal.cobertura_recente_percentual == 100.0
