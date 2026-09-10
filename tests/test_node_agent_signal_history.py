from pathlib import Path

import services.infra.node_agent as node_agent_module
from models.estado_node import EstadoNode
from services.infra.node_agent import (
    NodeHealthAgent,
)


def _estado():
    return EstadoNode(
        versao_schema=1,
        node_id="node-v113",
        coletado_em=("2026-09-10T13:10:00+00:00"),
        sistema="Windows",
        versao_sistema="10",
        arquitetura="AMD64",
        uptime_segundos=100.0,
        cpu_percentual=20.0,
        memoria_total_bytes=1000,
        memoria_disponivel_bytes=500,
        memoria_uso_percentual=50.0,
        disco_total_bytes=2000,
        disco_livre_bytes=1000,
        disco_uso_percentual=50.0,
        quantidade_processos_projeto=3,
        servicos=(),
        memoria_processos_projeto_bytes=100,
    )


def _agente(
    tmp_path,
    *,
    persistir_estado_sinais,
):
    estado = _estado()

    return NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado_atual.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: "node-v113",
        capturar_estado=(lambda *, node_id: estado),
        salvar_estado=(lambda valor, caminho: Path(caminho)),
        analisar_historico=(lambda diretorio: "ANALISE"),
        salvar_analise=(lambda valor, caminho: Path(caminho)),
        analisar_tendencia=(lambda diretorio: "TENDENCIA"),
        salvar_tendencia=(lambda valor, caminho: Path(caminho)),
        analisar_qualidade=(lambda diretorio, *, cadencia_nominal_segundos: ("QUALIDADE")),
        salvar_qualidade=(lambda valor, caminho: Path(caminho)),
        analisar_sinais=(lambda *args: "SINAIS"),
        salvar_sinais=(lambda valor, caminho: Path(caminho)),
        persistir_estado_sinais=(persistir_estado_sinais),
    )


def test_v113_analise_roda_depois_da_persistencia_temporal(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def persistir(
        sinais,
        *,
        caminho_estado,
        diretorio_historico,
    ):
        chamadas.append(
            (
                "persistir",
                sinais,
                Path(caminho_estado),
                Path(diretorio_historico),
            )
        )

        return object()

    def analisar(
        diretorio,
    ):
        chamadas.append(
            (
                "analisar",
                Path(diretorio),
            )
        )

        return "ANALISE_TEMPORAL"

    def salvar(
        analise,
        caminho,
    ):
        chamadas.append(
            (
                "salvar",
                analise,
                Path(caminho),
            )
        )

        return Path(caminho)

    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinais_node",
        analisar,
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_analise_historico_sinais_node",
        salvar,
    )

    agente = _agente(
        tmp_path,
        persistir_estado_sinais=persistir,
    )

    agente.executar_ciclo()

    assert chamadas == [
        (
            "persistir",
            "SINAIS",
            tmp_path / "sinais_estado_atual.json",
            tmp_path / "historico_sinais",
        ),
        (
            "analisar",
            tmp_path / "historico_sinais",
        ),
        (
            "salvar",
            "ANALISE_TEMPORAL",
            tmp_path / "analise_historico_sinais_atual.json",
        ),
    ]


def test_v113_falha_temporal_impede_analise_historica(
    tmp_path,
    monkeypatch,
):
    def persistir_falha(
        sinais,
        *,
        caminho_estado,
        diretorio_historico,
    ):
        del sinais
        del caminho_estado
        del diretorio_historico

        raise RuntimeError("falha proposital")

    def analisar_proibido(
        diretorio,
    ):
        del diretorio

        raise AssertionError("Analise historica nao deveria rodar.")

    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinais_node",
        analisar_proibido,
    )

    agente = _agente(
        tmp_path,
        persistir_estado_sinais=persistir_falha,
    )

    resultado = agente.executar_ciclo()

    assert resultado is not None

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()


def test_v113_falha_da_analise_historica_nao_quebra_ciclo(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def persistir(
        sinais,
        *,
        caminho_estado,
        diretorio_historico,
    ):
        del sinais
        del caminho_estado
        del diretorio_historico

        chamadas.append("persistiu")

        return object()

    def analisar_falha(
        diretorio,
    ):
        del diretorio

        chamadas.append("analisou")

        raise RuntimeError("falha proposital")

    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinais_node",
        analisar_falha,
    )

    agente = _agente(
        tmp_path,
        persistir_estado_sinais=persistir,
    )

    resultado = agente.executar_ciclo()

    assert resultado is not None

    assert chamadas == [
        "persistiu",
        "analisou",
    ]

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()


def test_v113_saida_derivada_fica_no_diretorio_do_estado(
    tmp_path,
    monkeypatch,
):
    caminhos = []

    def persistir(
        sinais,
        *,
        caminho_estado,
        diretorio_historico,
    ):
        del sinais
        del caminho_estado
        del diretorio_historico

        return object()

    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinais_node",
        lambda diretorio: "ANALISE_TEMPORAL",
    )

    def salvar(
        analise,
        caminho,
    ):
        del analise

        caminhos.append(Path(caminho))

        return Path(caminho)

    monkeypatch.setattr(
        node_agent_module,
        "salvar_analise_historico_sinais_node",
        salvar,
    )

    agente = _agente(
        tmp_path,
        persistir_estado_sinais=persistir,
    )

    agente.executar_ciclo()

    assert caminhos == [tmp_path / "analise_historico_sinais_atual.json"]
