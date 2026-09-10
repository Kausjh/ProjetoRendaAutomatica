from pathlib import Path

import services.infra.node_agent as node_agent_module
from models.estado_node import EstadoNode
from services.infra.node_agent import NodeHealthAgent


def _estado():
    return EstadoNode(
        versao_schema=1,
        node_id="node-v124",
        coletado_em=("2026-09-10T17:30:00+00:00"),
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
        obter_node_id=lambda: "node-v124",
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
    persistir_estado=None,
    analisar_historico_interpretacoes=None,
    salvar_analise_interpretacoes=None,
):
    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_sinais_node",
        lambda diretorio: "HISTORICO_SINAIS",
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
        lambda **kwargs: "QUALIDADE_TEMPORAL",
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_qualidade_temporal_evidencia_node",
        lambda analise, caminho: Path(caminho),
    )

    monkeypatch.setattr(
        node_agent_module,
        "interpretar_evidencias_node",
        lambda **kwargs: "INTERPRETACAO",
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_interpretacao_evidencias_node",
        lambda interpretacao, caminho: Path(caminho),
    )

    monkeypatch.setattr(
        node_agent_module,
        "persistir_estado_interpretacao_evidencias_node",
        (persistir_estado if persistir_estado is not None else lambda *args, **kwargs: "ESTADO"),
    )

    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_interpretacoes_node",
        (
            analisar_historico_interpretacoes
            if analisar_historico_interpretacoes is not None
            else lambda diretorio: "ANALISE_INTERPRETACOES"
        ),
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_analise_historico_interpretacoes_node",
        (
            salvar_analise_interpretacoes
            if salvar_analise_interpretacoes is not None
            else lambda analise, caminho: Path(caminho)
        ),
    )


def test_v124_analise_roda_depois_da_persistencia_temporal(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def persistir(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        chamadas.append("persistir")

        return "ESTADO"

    def analisar(
        diretorio,
    ):
        del diretorio

        chamadas.append("analisar")

        return "ANALISE"

    def salvar(
        analise,
        caminho,
    ):
        del analise
        del caminho

        chamadas.append("salvar")

        return Path("analise.json")

    _preparar_cadeia(
        monkeypatch,
        persistir_estado=persistir,
        analisar_historico_interpretacoes=analisar,
        salvar_analise_interpretacoes=salvar,
    )

    _agente(tmp_path).executar_ciclo()

    assert chamadas == [
        "persistir",
        "analisar",
        "salvar",
    ]


def test_v124_analise_recebe_historico_isolado_do_agente(
    tmp_path,
    monkeypatch,
):
    recebido = {}
    saidas = []

    def analisar(
        diretorio,
    ):
        recebido["diretorio"] = Path(diretorio)

        return "ANALISE"

    def salvar(
        analise,
        caminho,
    ):
        del analise

        saidas.append(Path(caminho))

        return Path(caminho)

    _preparar_cadeia(
        monkeypatch,
        analisar_historico_interpretacoes=analisar,
        salvar_analise_interpretacoes=salvar,
    )

    _agente(tmp_path).executar_ciclo()

    assert recebido == {"diretorio": (tmp_path / "historico_interpretacoes")}

    assert saidas == [tmp_path / "analise_historico_interpretacoes_atual.json"]


def test_v124_falha_persistencia_suprime_analise(
    tmp_path,
    monkeypatch,
):
    def persistir_falha(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        raise RuntimeError("falha proposital")

    def analisar_proibido(
        diretorio,
    ):
        del diretorio

        raise AssertionError("Analise historica nao deveria rodar.")

    _preparar_cadeia(
        monkeypatch,
        persistir_estado=persistir_falha,
        analisar_historico_interpretacoes=analisar_proibido,
    )

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None


def test_v124_falha_analise_historica_nao_quebra_ciclo(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def analisar_falha(
        diretorio,
    ):
        del diretorio

        chamadas.append("analisar")

        raise RuntimeError("falha proposital")

    _preparar_cadeia(
        monkeypatch,
        analisar_historico_interpretacoes=analisar_falha,
    )

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None

    assert chamadas == ["analisar"]

    assert (tmp_path / "historico" / "2026-09-10.jsonl").exists()


def test_v124_falha_salvar_analise_nao_quebra_ciclo(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def salvar_falha(
        analise,
        caminho,
    ):
        del analise
        del caminho

        chamadas.append("salvar")

        raise RuntimeError("falha proposital")

    _preparar_cadeia(
        monkeypatch,
        salvar_analise_interpretacoes=salvar_falha,
    )

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None

    assert chamadas == ["salvar"]


def test_v124_analise_historica_nao_altera_resultado_do_ciclo(
    tmp_path,
    monkeypatch,
):
    _preparar_cadeia(monkeypatch)

    resultado = _agente(tmp_path).executar_ciclo()

    assert resultado is not None
    assert resultado.node_id == "node-v124"
