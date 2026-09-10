import json

import pytest

from services.infra.node_data_quality import (
    analisar_qualidade_dados_node,
    salvar_qualidade_dados_node,
)


def _gravar(
    caminho,
    registros,
):
    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    caminho.write_text(
        "\n".join(json.dumps(registro) for registro in registros) + "\n",
        encoding="utf-8",
    )


def test_janelas_regulares_tem_contagem_esperada(
    tmp_path,
):
    historico = tmp_path / "historico"

    registros = []

    for minuto in range(
        0,
        181,
        30,
    ):
        hora = minuto // 60
        minuto_hora = minuto % 60

        registros.append(
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T" f"{hora:02d}:" f"{minuto_hora:02d}:" "00+00:00"),
                "cpu_percentual": 10,
                "memoria_uso_percentual": 60,
                "quantidade_processos_projeto": 20,
                "servicos": [],
            }
        )

    _gravar(
        historico / "2026-09-10.jsonl",
        registros,
    )

    analise = analisar_qualidade_dados_node(
        historico,
        janela_recente_minutos=60,
        janela_baseline_minutos=120,
        cadencia_nominal_segundos=1800,
    )

    assert analise.janela_recente.amostras_esperadas == 3

    assert analise.janela_recente.amostras_observadas == 3

    assert analise.janela_baseline.amostras_esperadas == 4

    assert analise.janela_baseline.amostras_observadas == 4

    assert analise.janela_recente.maior_gap_segundos == 1800

    assert analise.janela_recente.gaps_igual_ou_acima_2x_cadencia == 0


def test_gap_grande_e_detectado(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "coletado_em": ("2026-09-10T00:00:00+00:00"),
                "cpu_percentual": 10,
                "servicos": [],
            },
            {
                "coletado_em": ("2026-09-10T00:05:00+00:00"),
                "cpu_percentual": 10,
                "servicos": [],
            },
            {
                "coletado_em": ("2026-09-10T00:15:00+00:00"),
                "cpu_percentual": 10,
                "servicos": [],
            },
        ],
    )

    analise = analisar_qualidade_dados_node(
        historico,
        janela_recente_minutos=15,
        janela_baseline_minutos=15,
        cadencia_nominal_segundos=300,
    )

    janela = analise.janela_recente

    assert janela.amostras_esperadas == 4
    assert janela.amostras_observadas == 3
    assert janela.maior_gap_segundos == 600

    assert janela.maior_gap_multiplo_cadencia == 2

    assert janela.gaps_igual_ou_acima_2x_cadencia == 1


def test_ram_pre_v13_fica_sem_comparacao(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "coletado_em": ("2026-09-10T00:00:00+00:00"),
                "memoria_uso_percentual": 60,
                "servicos": [],
            },
            {
                "coletado_em": ("2026-09-10T01:00:00+00:00"),
                "memoria_uso_percentual": 65,
                "servicos": [],
            },
            {
                "coletado_em": ("2026-09-10T02:00:00+00:00"),
                "memoria_uso_percentual": 70,
                "memoria_processos_projeto_bytes": 1000,
                "servicos": [],
            },
        ],
    )

    analise = analisar_qualidade_dados_node(
        historico,
        janela_recente_minutos=60,
        janela_baseline_minutos=60,
        cadencia_nominal_segundos=3600,
    )

    projeto = next(
        metrica for metrica in analise.metricas if metrica.nome == "memoria_processos_projeto_bytes"
    )

    assert projeto.amostras_com_valor_recente == 1

    assert projeto.amostras_com_valor_baseline == 0

    assert projeto.comparacao_disponivel is False

    assert projeto.inclinacao_recente_disponivel is False


def test_memoria_de_servico_tem_cobertura_propria(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "coletado_em": ("2026-09-10T00:00:00+00:00"),
                "servicos": [
                    {
                        "nome": "runtime",
                        "ativo": True,
                    }
                ],
            },
            {
                "coletado_em": ("2026-09-10T01:00:00+00:00"),
                "servicos": [
                    {
                        "nome": "runtime",
                        "ativo": True,
                        "memoria_rss_bytes": 100,
                    }
                ],
            },
            {
                "coletado_em": ("2026-09-10T02:00:00+00:00"),
                "servicos": [
                    {
                        "nome": "runtime",
                        "ativo": True,
                        "memoria_rss_bytes": 120,
                    }
                ],
            },
        ],
    )

    analise = analisar_qualidade_dados_node(
        historico,
        janela_recente_minutos=60,
        janela_baseline_minutos=60,
        cadencia_nominal_segundos=3600,
    )

    runtime = next(servico for servico in analise.servicos if servico.nome == "runtime")

    assert runtime.amostras_observadas_recente == 2

    assert runtime.amostras_observadas_baseline == 1

    assert runtime.memoria_rss_bytes.amostras_com_valor_recente == 2

    assert runtime.memoria_rss_bytes.amostras_com_valor_baseline == 0

    assert runtime.memoria_rss_bytes.comparacao_disponivel is False

    assert runtime.memoria_rss_bytes.inclinacao_recente_disponivel is True


def test_qualidade_nao_cria_politica_de_saude(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T00:00:00+00:00"),
                "cpu_percentual": 100,
                "memoria_uso_percentual": 100,
                "servicos": [],
            },
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T01:00:00+00:00"),
                "cpu_percentual": 100,
                "memoria_uso_percentual": 100,
                "servicos": [],
            },
        ],
    )

    texto = json.dumps(
        analisar_qualidade_dados_node(
            historico,
            janela_recente_minutos=30,
            janela_baseline_minutos=60,
            cadencia_nominal_segundos=300,
        ).para_dict()
    )

    for termo in (
        "status_saude",
        "precisa_reiniciar",
        "reboot_recomendado",
        "acao_recomendada",
        "saudavel",
        "degradado",
    ):
        assert termo not in texto


def test_salvamento_e_atomico(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "coletado_em": ("2026-09-10T00:00:00+00:00"),
                "cpu_percentual": 10,
                "servicos": [],
            }
        ],
    )

    analise = analisar_qualidade_dados_node(historico)

    caminho = tmp_path / "qualidade.json"

    resultado = salvar_qualidade_dados_node(
        analise,
        caminho,
    )

    assert resultado == caminho
    assert caminho.exists()

    assert not caminho.with_suffix(".json.tmp").exists()


def test_parametros_invalidos_sao_rejeitados(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="janela_recente_minutos",
    ):
        analisar_qualidade_dados_node(
            tmp_path,
            janela_recente_minutos=0,
        )

    with pytest.raises(
        ValueError,
        match="janela_baseline_minutos",
    ):
        analisar_qualidade_dados_node(
            tmp_path,
            janela_baseline_minutos=0,
        )

    with pytest.raises(
        ValueError,
        match="cadencia_nominal_segundos",
    ):
        analisar_qualidade_dados_node(
            tmp_path,
            cadencia_nominal_segundos=0,
        )


def test_razao_bruta_pode_superar_100_mas_cobertura_nao(
    tmp_path,
):
    historico = tmp_path / "historico"

    registros = [
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:00:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:04:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:08:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:12:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:15:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
    ]

    _gravar(
        historico / "2026-09-10.jsonl",
        registros,
    )

    janela = analisar_qualidade_dados_node(
        historico,
        janela_recente_minutos=15,
        janela_baseline_minutos=15,
        cadencia_nominal_segundos=300,
    ).janela_recente

    assert janela.amostras_esperadas == 4
    assert janela.amostras_observadas == 5

    assert janela.razao_amostras_percentual == 125.0
    assert janela.cobertura_normalizada_percentual == 100.0
    assert janela.amostras_excedentes == 1


def test_timestamps_distintos_sao_separados_das_amostras(
    tmp_path,
):
    historico = tmp_path / "historico"

    registros = [
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:00:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:10:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:10:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:15:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
    ]

    _gravar(
        historico / "2026-09-10.jsonl",
        registros,
    )

    janela = analisar_qualidade_dados_node(
        historico,
        janela_recente_minutos=15,
        janela_baseline_minutos=15,
        cadencia_nominal_segundos=300,
    ).janela_recente

    assert janela.amostras_observadas == 4
    assert janela.timestamps_distintos == 3
    assert janela.timestamps_repetidos == 1


def test_gap_de_borda_nao_altera_gap_interno_legado(
    tmp_path,
):
    historico = tmp_path / "historico"

    registros = [
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:10:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
        {
            "node_id": "node-v117",
            "coletado_em": "2026-09-10T00:15:00+00:00",
            "cpu_percentual": 10,
            "servicos": [],
        },
    ]

    _gravar(
        historico / "2026-09-10.jsonl",
        registros,
    )

    janela = analisar_qualidade_dados_node(
        historico,
        janela_recente_minutos=15,
        janela_baseline_minutos=15,
        cadencia_nominal_segundos=300,
    ).janela_recente

    assert janela.maior_gap_segundos == 300.0
    assert janela.gaps_igual_ou_acima_2x_cadencia == 0

    assert janela.gap_borda_inicio_segundos == 600.0
    assert janela.gap_borda_fim_segundos == 0.0

    assert janela.maior_gap_com_bordas_segundos == 600.0

    assert janela.maior_gap_com_bordas_multiplo_cadencia == 2.0

    assert janela.gaps_com_bordas_igual_ou_acima_2x_cadencia == 1


def test_janela_sem_amostras_tem_gap_total_observavel(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "node_id": "node-v117",
                "coletado_em": "2026-09-10T01:00:00+00:00",
                "cpu_percentual": 10,
                "servicos": [],
            }
        ],
    )

    janela = analisar_qualidade_dados_node(
        historico,
        janela_recente_minutos=30,
        janela_baseline_minutos=30,
        cadencia_nominal_segundos=300,
    ).janela_baseline

    assert janela.amostras_observadas == 0
    assert janela.timestamps_distintos == 0

    assert janela.gap_borda_inicio_segundos is None
    assert janela.gap_borda_fim_segundos is None
    assert janela.maior_gap_com_bordas_segundos == 1800.0

    assert janela.gaps_com_bordas_igual_ou_acima_2x_cadencia == 1
