import json

import pytest

from services.infra.node_trend_analysis import (
    analisar_tendencia_node,
    salvar_tendencia_node,
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


def test_compara_janela_recente_com_baseline(
    tmp_path,
):
    historico = tmp_path / "historico"

    registros = []

    valores = [
        50,
        60,
        70,
        80,
        90,
    ]

    ativos = [
        True,
        True,
        True,
        False,
        True,
    ]

    for indice, minuto in enumerate(
        (
            0,
            30,
            60,
            90,
            120,
        )
    ):
        hora = minuto // 60
        minuto_hora = minuto % 60

        registro = {
            "node_id": "node-a1b2c3d4e5f6",
            "coletado_em": ("2026-09-10T" f"{hora:02d}:" f"{minuto_hora:02d}:" "00+00:00"),
            "cpu_percentual": valores[indice],
            "memoria_uso_percentual": valores[indice],
            "quantidade_processos_projeto": (10 + indice * 10),
            "servicos": [
                {
                    "nome": "runtime",
                    "ativo": ativos[indice],
                    "memoria_rss_bytes": (100 + indice * 10),
                }
            ],
        }

        if indice >= 2:
            registro["memoria_processos_projeto_bytes"] = 1000 + indice * 100

        registros.append(registro)

    _gravar(
        historico / "2026-09-10.jsonl",
        registros,
    )

    analise = analisar_tendencia_node(
        historico,
        janela_recente_minutos=60,
        janela_baseline_minutos=120,
    )

    assert analise.quantidade_amostras_recente == 3

    assert analise.quantidade_amostras_baseline == 2

    memoria = analise.memoria_host_percentual

    assert memoria.atual == 90
    assert memoria.media_recente == 80
    assert memoria.media_baseline == 55
    assert memoria.delta_media_absoluto == 25

    assert memoria.delta_media_percentual == pytest.approx(45.4545454545)

    assert memoria.inclinacao_recente_por_hora == pytest.approx(20)

    projeto = analise.memoria_processos_projeto_bytes

    assert projeto.amostras_recente == 3
    assert projeto.amostras_baseline == 0
    assert projeto.media_baseline is None
    assert projeto.delta_media_absoluto is None

    runtime = next(servico for servico in analise.servicos if servico.nome == "runtime")

    assert runtime.percentual_ativo_baseline == 100

    assert runtime.percentual_ativo_recente == pytest.approx(66.6666666667)

    assert runtime.delta_percentual_ativo_pontos == pytest.approx(-33.3333333333)


def test_dados_pre_v13_nao_fabricam_memoria(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T00:00:00+00:00"),
                "memoria_uso_percentual": 60,
                "servicos": [
                    {
                        "nome": "runtime",
                        "ativo": True,
                    }
                ],
            },
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T01:00:00+00:00"),
                "memoria_uso_percentual": 65,
                "servicos": [
                    {
                        "nome": "runtime",
                        "ativo": True,
                    }
                ],
            },
        ],
    )

    analise = analisar_tendencia_node(
        historico,
        janela_recente_minutos=30,
        janela_baseline_minutos=60,
    )

    projeto = analise.memoria_processos_projeto_bytes

    assert projeto.atual is None
    assert projeto.media_recente is None
    assert projeto.media_baseline is None

    runtime = analise.servicos[0]

    assert runtime.memoria_rss_bytes.atual is None


def test_baseline_e_recente_nao_se_sobrepoem(
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
                "coletado_em": ("2026-09-10T01:00:00+00:00"),
                "cpu_percentual": 20,
                "servicos": [],
            },
            {
                "coletado_em": ("2026-09-10T02:00:00+00:00"),
                "cpu_percentual": 30,
                "servicos": [],
            },
        ],
    )

    analise = analisar_tendencia_node(
        historico,
        janela_recente_minutos=60,
        janela_baseline_minutos=60,
    )

    assert analise.cpu_percentual.amostras_recente == 2

    assert analise.cpu_percentual.amostras_baseline == 1

    assert analise.cpu_percentual.media_recente == 25

    assert analise.cpu_percentual.media_baseline == 10


def test_sem_politica_de_saude_ou_reboot(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T00:00:00+00:00"),
                "cpu_percentual": 99,
                "memoria_uso_percentual": 99,
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
        analisar_tendencia_node(
            historico,
            janela_recente_minutos=30,
            janela_baseline_minutos=60,
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

    analise = analisar_tendencia_node(historico)

    caminho = tmp_path / "tendencia.json"

    resultado = salvar_tendencia_node(
        analise,
        caminho,
    )

    assert resultado == caminho
    assert caminho.exists()

    assert not caminho.with_suffix(".json.tmp").exists()


def test_janelas_invalidas_sao_rejeitadas(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="janela_recente_minutos",
    ):
        analisar_tendencia_node(
            tmp_path,
            janela_recente_minutos=0,
        )

    with pytest.raises(
        ValueError,
        match="janela_baseline_minutos",
    ):
        analisar_tendencia_node(
            tmp_path,
            janela_baseline_minutos=0,
        )
