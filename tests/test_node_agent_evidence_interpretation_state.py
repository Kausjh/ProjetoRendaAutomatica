from pathlib import Path

import services.infra.node_agent as node_agent_module
from models.estado_node import EstadoNode
from services.infra.node_agent import NodeHealthAgent


def _estado():
    return EstadoNode(
        versao_schema=1,
        node_id="node-v122",
        coletado_em=("2026-09-10T17:00:00+00:00"),
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


def _persistencia_sinais_ok(
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
        obter_node_id=lambda: "node-v122",
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
        persistir_estado_sinais=(_persistencia_sinais_ok),
    )


def _preparar_cadeia(
    monkeypatch,
    *,
    interpretar=None,
    salvar_interpretacao=None,
    persistir_estado=None,
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
        lambda **kwargs: "TEMPORAL",
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_qualidade_temporal_evidencia_node",
        lambda analise, caminho: Path(caminho),
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

    monkeypatch.setattr(
        node_agent_module,
        "persistir_estado_interpretacao_evidencias_node",
        (persistir_estado if persistir_estado is not None else lambda *args, **kwargs: "ESTADO"),
    )


def test_v122_estado_roda_depois_de_salvar_interpretacao(
    tmp_path,
    monkeypatch,
):
    chamadas = []

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

    def persistir_estado(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        chamadas.append("persistir_estado")

        return "ESTADO"

    _preparar_cadeia(
        monkeypatch,
        interpretar=interpretar,
        salvar_interpretacao=salvar_interpretacao,
        persistir_estado=persistir_estado,
    )

    _agente(tmp_path).executar_ciclo()

    assert chamadas == [
        "interpretar",
        "salvar_interpretacao",
        "persistir_estado",
    ]


def test_v122_estado_recebe_caminhos_isolados_do_agente(
    tmp_path,
    monkeypatch,
):
    recebido = {}

    def persistir_estado(
        caminho_interpretacao,
        **kwargs,
    ):
        recebido["caminho_interpretacao"] = Path(caminho_interpretacao)

        recebido.update({chave: Path(valor) for chave, valor in kwargs.items()})

        return "ESTADO"

    _preparar_cadeia(
        monkeypatch,
        persistir_estado=persistir_estado,
    )

    _agente(tmp_path).executar_ciclo()

    assert recebido == {
        "caminho_interpretacao": (tmp_path / "interpretacao_evidencias_atual.json"),
        "caminho_estado": (tmp_path / "interpretacao_estado_atual.json"),
        "diretorio_historico": (tmp_path / "historico_interpretacoes"),
    }


def test_v122_falha_interpretacao_suprime_estado(
    tmp_path,
    monkeypatch,
):
    def interpretar_falha(
        **kwargs,
    ):
        del kwargs

        raise RuntimeError("falha proposital")

    def estado_proibido(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        raise AssertionError("Estado temporal nao deveria rodar.")

    _preparar_cadeia(
        monkeypatch,
        interpretar=interpretar_falha,
        persistir_estado=estado_proibido,
    )

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None


def test_v122_falha_salvar_interpretacao_suprime_estado(
    tmp_path,
    monkeypatch,
):
    def salvar_falha(
        interpretacao,
        caminho,
    ):
        del interpretacao
        del caminho

        raise RuntimeError("falha proposital")

    def estado_proibido(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        raise AssertionError("Estado temporal nao deveria rodar.")

    _preparar_cadeia(
        monkeypatch,
        salvar_interpretacao=salvar_falha,
        persistir_estado=estado_proibido,
    )

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None


def test_v122_falha_estado_temporal_nao_quebra_ciclo(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def persistir_falha(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        chamadas.append("persistir_estado")

        raise RuntimeError("falha proposital")

    _preparar_cadeia(
        monkeypatch,
        persistir_estado=persistir_falha,
    )

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None

    assert chamadas == ["persistir_estado"]

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()


def test_v122_estado_temporal_nao_altera_resultado_do_ciclo(
    tmp_path,
    monkeypatch,
):
    _preparar_cadeia(monkeypatch)

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None
    assert resultado.node_id == "node-v122"
