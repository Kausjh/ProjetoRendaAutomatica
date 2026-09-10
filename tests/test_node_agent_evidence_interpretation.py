from pathlib import Path

import services.infra.node_agent as node_agent_module
from models.estado_node import EstadoNode
from services.infra.node_agent import NodeHealthAgent


def _estado():
    return EstadoNode(
        versao_schema=1,
        node_id="node-v120",
        coletado_em=("2026-09-10T16:30:00+00:00"),
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


def _agente(
    tmp_path,
):
    estado = _estado()

    return NodeHealthAgent(
        intervalo_segundos=300,
        caminho_estado=(tmp_path / "estado_atual.json"),
        diretorio_historico=(tmp_path / "historico"),
        obter_node_id=lambda: "node-v120",
        capturar_estado=(lambda *, node_id: estado),
        salvar_estado=(lambda valor, caminho: Path(caminho)),
        analisar_historico=(lambda diretorio: "ANALISE"),
        salvar_analise=(lambda valor, caminho: Path(caminho)),
        analisar_tendencia=(lambda diretorio: "TENDENCIA"),
        salvar_tendencia=(lambda valor, caminho: Path(caminho)),
        analisar_qualidade=(lambda diretorio, *, cadencia_nominal_segundos: "QUALIDADE"),
        salvar_qualidade=(lambda valor, caminho: Path(caminho)),
        analisar_sinais=(lambda *args: "SINAIS"),
        salvar_sinais=(lambda valor, caminho: Path(caminho)),
        persistir_estado_sinais=(_persistencia_ok),
    )


def _preparar_cadeia(
    monkeypatch,
    *,
    analisar_temporal=None,
    salvar_temporal=None,
    interpretar=None,
    salvar_interpretacao=None,
):
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

    monkeypatch.setattr(
        node_agent_module,
        "gerar_resumo_evidencias_node",
        lambda **kwargs: "RESUMO",
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_resumo_evidencias_node",
        lambda resumo, caminho: Path(caminho),
    )

    monkeypatch.setattr(
        node_agent_module,
        "analisar_qualidade_temporal_evidencia_node",
        (analisar_temporal if analisar_temporal is not None else lambda **kwargs: "TEMPORAL"),
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_qualidade_temporal_evidencia_node",
        (
            salvar_temporal
            if salvar_temporal is not None
            else lambda analise, caminho: Path(caminho)
        ),
    )

    monkeypatch.setattr(
        node_agent_module,
        "interpretar_evidencias_node",
        (interpretar if interpretar is not None else lambda **kwargs: "INTERPRETACAO"),
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_interpretacao_evidencias_node",
        (
            salvar_interpretacao
            if salvar_interpretacao is not None
            else lambda interpretacao, caminho: Path(caminho)
        ),
    )


def test_v120_interpretacao_roda_depois_da_qualidade_temporal(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def analisar_temporal(
        **kwargs,
    ):
        del kwargs

        chamadas.append("analisar_temporal")

        return "TEMPORAL"

    def salvar_temporal(
        analise,
        caminho,
    ):
        del analise
        del caminho

        chamadas.append("salvar_temporal")

        return Path("temporal.json")

    def interpretar(
        **kwargs,
    ):
        del kwargs

        chamadas.append("interpretar")

        return "INTERPRETACAO"

    def salvar_interpretacao(
        interpretacao,
        caminho,
    ):
        del interpretacao
        del caminho

        chamadas.append("salvar_interpretacao")

        return Path("interpretacao.json")

    _preparar_cadeia(
        monkeypatch,
        analisar_temporal=analisar_temporal,
        salvar_temporal=salvar_temporal,
        interpretar=interpretar,
        salvar_interpretacao=salvar_interpretacao,
    )

    _agente(tmp_path).executar_ciclo()

    assert chamadas == [
        "analisar_temporal",
        "salvar_temporal",
        "interpretar",
        "salvar_interpretacao",
    ]


def test_v120_interpretacao_recebe_artefatos_do_mesmo_ciclo(
    tmp_path,
    monkeypatch,
):
    recebido = {}
    saidas = []

    def interpretar(
        **kwargs,
    ):
        recebido.update({chave: Path(valor) for chave, valor in kwargs.items()})

        return "INTERPRETACAO"

    def salvar_interpretacao(
        interpretacao,
        caminho,
    ):
        del interpretacao

        saidas.append(Path(caminho))

        return Path(caminho)

    _preparar_cadeia(
        monkeypatch,
        interpretar=interpretar,
        salvar_interpretacao=(salvar_interpretacao),
    )

    _agente(tmp_path).executar_ciclo()

    assert recebido == {
        "caminho_resumo": (tmp_path / "resumo_evidencias_atual.json"),
        "caminho_qualidade_temporal": (tmp_path / "qualidade_evidencia_temporal_atual.json"),
    }

    assert saidas == [tmp_path / "interpretacao_evidencias_atual.json"]


def test_v120_falha_analise_temporal_suprime_interpretacao(
    tmp_path,
    monkeypatch,
):
    def analisar_falha(
        **kwargs,
    ):
        del kwargs

        raise RuntimeError("falha proposital")

    def interpretar_proibido(
        **kwargs,
    ):
        del kwargs

        raise AssertionError("Interpretacao nao deveria rodar.")

    _preparar_cadeia(
        monkeypatch,
        analisar_temporal=analisar_falha,
        interpretar=interpretar_proibido,
    )

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None


def test_v120_falha_salvar_temporal_suprime_interpretacao(
    tmp_path,
    monkeypatch,
):
    def salvar_falha(
        analise,
        caminho,
    ):
        del analise
        del caminho

        raise RuntimeError("falha proposital")

    def interpretar_proibido(
        **kwargs,
    ):
        del kwargs

        raise AssertionError("Interpretacao nao deveria rodar.")

    _preparar_cadeia(
        monkeypatch,
        salvar_temporal=salvar_falha,
        interpretar=interpretar_proibido,
    )

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None


def test_v120_falha_interpretacao_nao_quebra_ciclo(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def interpretar_falha(
        **kwargs,
    ):
        del kwargs

        chamadas.append("interpretar")

        raise RuntimeError("falha proposital")

    _preparar_cadeia(
        monkeypatch,
        interpretar=interpretar_falha,
    )

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None

    assert chamadas == ["interpretar"]

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()


def test_v120_falha_salvar_interpretacao_nao_quebra_ciclo(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def salvar_falha(
        interpretacao,
        caminho,
    ):
        del interpretacao
        del caminho

        chamadas.append("salvar_interpretacao")

        raise RuntimeError("falha proposital")

    _preparar_cadeia(
        monkeypatch,
        salvar_interpretacao=salvar_falha,
    )

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None

    assert chamadas == ["salvar_interpretacao"]
