import json

import pytest

from services.infra.node_history_analysis import (
    analisar_historico_node,
    carregar_historico_node,
    salvar_analise_node,
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


def test_analise_aceita_historico_misto_pre_e_pos_v13(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T00:00:00+00:00"),
                "uptime_segundos": 100,
                "cpu_percentual": 10,
                "memoria_uso_percentual": 50,
                "quantidade_processos_projeto": 10,
                "servicos": [
                    {
                        "nome": "runtime",
                        "ativo": True,
                    }
                ],
            },
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T00:05:00+00:00"),
                "uptime_segundos": 400,
                "cpu_percentual": 20,
                "memoria_uso_percentual": 60,
                "memoria_processos_projeto_bytes": 100,
                "quantidade_processos_projeto": 20,
                "servicos": [
                    {
                        "nome": "runtime",
                        "ativo": True,
                        "memoria_rss_bytes": 30,
                    }
                ],
            },
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T00:10:00+00:00"),
                "uptime_segundos": 50,
                "cpu_percentual": 30,
                "memoria_uso_percentual": 70,
                "memoria_processos_projeto_bytes": 150,
                "quantidade_processos_projeto": 30,
                "servicos": [
                    {
                        "nome": "runtime",
                        "ativo": False,
                        "memoria_rss_bytes": 40,
                    }
                ],
            },
        ],
    )

    analise = analisar_historico_node(historico)

    assert analise.quantidade_amostras == 3
    assert analise.quantidade_amostras_v13 == 2
    assert analise.reinicios_detectados == 1

    assert analise.cpu_percentual.atual == 30
    assert analise.cpu_percentual.minimo == 10
    assert analise.cpu_percentual.maximo == 30
    assert analise.cpu_percentual.media == 20
    assert analise.cpu_percentual.mediana == 20
    assert analise.cpu_percentual.delta_primeira_ultima == 20

    assert analise.memoria_processos_projeto_bytes.atual == 150

    assert analise.memoria_processos_projeto_bytes.quantidade_amostras == 2

    runtime = next(servico for servico in analise.servicos if servico.nome == "runtime")

    assert runtime.amostras_observadas == 3
    assert runtime.amostras_ativas == 2
    assert runtime.memoria_rss_bytes.atual == 40


def test_linhas_invalidas_sao_ignoradas(
    tmp_path,
):
    historico = tmp_path / "historico"

    caminho = historico / "2026-09-10.jsonl"

    historico.mkdir()

    caminho.write_text(
        '{"coletado_em":"invalido"}\n'
        "nao-json\n"
        '{"coletado_em":'
        '"2026-09-10T00:00:00+00:00",'
        '"cpu_percentual":12}\n',
        encoding="utf-8",
    )

    registros = carregar_historico_node(historico)

    assert len(registros) == 1
    assert registros[0]["cpu_percentual"] == 12


def test_limites_usam_dias_e_amostras_mais_recentes(
    tmp_path,
):
    historico = tmp_path / "historico"

    for dia in range(
        1,
        5,
    ):
        _gravar(
            historico / f"2026-09-0{dia}.jsonl",
            [
                {
                    "coletado_em": (f"2026-09-0{dia}" "T00:00:00+00:00"),
                    "cpu_percentual": dia,
                },
                {
                    "coletado_em": (f"2026-09-0{dia}" "T00:05:00+00:00"),
                    "cpu_percentual": (dia + 10),
                },
            ],
        )

    registros = carregar_historico_node(
        historico,
        maximo_arquivos=2,
        maximo_amostras=3,
    )

    assert len(registros) == 3

    assert [item["cpu_percentual"] for item in registros] == [
        13,
        4,
        14,
    ]


def test_analise_nao_cria_politica_de_saude(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T00:00:00+00:00"),
                "uptime_segundos": 999999,
                "cpu_percentual": 99,
                "memoria_uso_percentual": 99,
                "memoria_processos_projeto_bytes": (999999999),
                "quantidade_processos_projeto": 999,
                "servicos": [],
            }
        ],
    )

    dados = analisar_historico_node(historico).para_dict()

    assert "status_saude" not in dados
    assert "precisa_reiniciar" not in dados
    assert "reboot_recomendado" not in dados
    assert "acao_recomendada" not in dados


def test_salvar_analise_e_atomico(
    tmp_path,
):
    historico = tmp_path / "historico"

    _gravar(
        historico / "2026-09-10.jsonl",
        [
            {
                "node_id": "node-a1b2c3d4e5f6",
                "coletado_em": ("2026-09-10T00:00:00+00:00"),
                "cpu_percentual": 10,
                "servicos": [],
            }
        ],
    )

    analise = analisar_historico_node(historico)

    caminho = tmp_path / "analise.json"

    resultado = salvar_analise_node(
        analise,
        caminho,
    )

    assert resultado == caminho
    assert caminho.exists()

    temporario = caminho.with_suffix(".json.tmp")

    assert not temporario.exists()

    dados = json.loads(
        caminho.read_text(
            encoding="utf-8",
        )
    )

    assert dados["quantidade_amostras"] == 1


def test_configuracao_invalida_e_rejeitada(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="maximo_arquivos",
    ):
        carregar_historico_node(
            tmp_path,
            maximo_arquivos=0,
        )

    with pytest.raises(
        ValueError,
        match="maximo_amostras",
    ):
        carregar_historico_node(
            tmp_path,
            maximo_amostras=0,
        )
