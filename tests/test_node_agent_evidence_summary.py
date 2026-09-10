from pathlib import Path

import services.infra.node_agent as node_agent_module
from models.estado_node import EstadoNode
from services.infra.node_agent import (
    NodeHealthAgent,
)


def _estado():
    return EstadoNode(
        versao_schema=1,
        node_id="node-v115",
        coletado_em=("2026-09-10T13:30:00+00:00"),
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
        obter_node_id=lambda: "node-v115",
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


def _persistencia_ok(
    sinais,
    *,
    caminho_estado,
    diretorio_historico,
):
    del sinais
    del caminho_estado
    del diretorio_historico

    return object()


def test_v115_resumo_roda_depois_da_analise_historica(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def analisar_historico(
        diretorio,
    ):
        chamadas.append(
            (
                "analisar_historico",
                Path(diretorio),
            )
        )

        return "HISTORICO"

    def salvar_historico(
        analise,
        caminho,
    ):
        chamadas.append(
            (
                "salvar_historico",
                analise,
                Path(caminho),
            )
        )

        return Path(caminho)

    def gerar_resumo(
        **kwargs,
    ):
        chamadas.append(
            (
                "gerar_resumo",
                {chave: Path(valor) for chave, valor in kwargs.items()},
            )
        )

        return "RESUMO"

    def salvar_resumo(
        resumo,
        caminho,
    ):
        chamadas.append(
            (
                "salvar_resumo",
                resumo,
                Path(caminho),
            )
        )

        return Path(caminho)

    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinais_node",
        analisar_historico,
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_analise_historico_sinais_node",
        salvar_historico,
    )

    monkeypatch.setattr(
        node_agent_module,
        "gerar_resumo_evidencias_node",
        gerar_resumo,
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_resumo_evidencias_node",
        salvar_resumo,
    )

    agente = _agente(
        tmp_path,
        persistir_estado_sinais=(_persistencia_ok),
    )

    agente.executar_ciclo()

    assert [item[0] for item in chamadas] == [
        "analisar_historico",
        "salvar_historico",
        "gerar_resumo",
        "salvar_resumo",
    ]


def test_v115_resumo_recebe_artefatos_do_mesmo_diretorio(
    tmp_path,
    monkeypatch,
):
    recebido = {}

    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinais_node",
        lambda diretorio: "HISTORICO",
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_analise_historico_sinais_node",
        lambda analise, caminho: Path(caminho),
    )

    def gerar(
        **kwargs,
    ):
        recebido.update({chave: Path(valor) for chave, valor in kwargs.items()})

        return "RESUMO"

    caminhos_saida = []

    monkeypatch.setattr(
        node_agent_module,
        "gerar_resumo_evidencias_node",
        gerar,
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_resumo_evidencias_node",
        lambda resumo, caminho: (caminhos_saida.append(Path(caminho)) or Path(caminho)),
    )

    agente = _agente(
        tmp_path,
        persistir_estado_sinais=(_persistencia_ok),
    )

    agente.executar_ciclo()

    assert recebido == {
        "caminho_sinais": (tmp_path / "sinais_atual.json"),
        "caminho_estado_temporal": (tmp_path / "sinais_estado_atual.json"),
        "caminho_historico_sinais": (tmp_path / "analise_historico_sinais_atual.json"),
        "caminho_qualidade": (tmp_path / "qualidade_atual.json"),
    }

    assert caminhos_saida == [tmp_path / "resumo_evidencias_atual.json"]


def test_v115_falha_analise_historica_suprime_resumo(
    tmp_path,
    monkeypatch,
):
    def analisar_falha(
        diretorio,
    ):
        del diretorio

        raise RuntimeError("falha proposital")

    def resumo_proibido(
        **kwargs,
    ):
        del kwargs

        raise AssertionError("Resumo nao deveria rodar.")

    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinais_node",
        analisar_falha,
    )

    monkeypatch.setattr(
        node_agent_module,
        "gerar_resumo_evidencias_node",
        resumo_proibido,
    )

    agente = _agente(
        tmp_path,
        persistir_estado_sinais=(_persistencia_ok),
    )

    resultado = agente.executar_ciclo()

    assert resultado is not None

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()


def test_v115_falha_salvar_analise_suprime_resumo(
    tmp_path,
    monkeypatch,
):
    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinais_node",
        lambda diretorio: "HISTORICO",
    )

    def salvar_falha(
        analise,
        caminho,
    ):
        del analise
        del caminho

        raise RuntimeError("falha proposital")

    def resumo_proibido(
        **kwargs,
    ):
        del kwargs

        raise AssertionError("Resumo nao deveria rodar.")

    monkeypatch.setattr(
        node_agent_module,
        "salvar_analise_historico_sinais_node",
        salvar_falha,
    )

    monkeypatch.setattr(
        node_agent_module,
        "gerar_resumo_evidencias_node",
        resumo_proibido,
    )

    agente = _agente(
        tmp_path,
        persistir_estado_sinais=(_persistencia_ok),
    )

    resultado = agente.executar_ciclo()

    assert resultado is not None


def test_v115_falha_resumo_nao_quebra_ciclo(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinais_node",
        lambda diretorio: "HISTORICO",
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_analise_historico_sinais_node",
        lambda analise, caminho: Path(caminho),
    )

    def gerar_falha(
        **kwargs,
    ):
        del kwargs

        chamadas.append("resumo")

        raise RuntimeError("falha proposital")

    monkeypatch.setattr(
        node_agent_module,
        "gerar_resumo_evidencias_node",
        gerar_falha,
    )

    agente = _agente(
        tmp_path,
        persistir_estado_sinais=(_persistencia_ok),
    )

    resultado = agente.executar_ciclo()

    assert resultado is not None

    assert chamadas == ["resumo"]

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()
