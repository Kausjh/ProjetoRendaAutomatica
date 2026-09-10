from pathlib import Path

import services.infra.node_agent as node_agent_module
from services.infra.node_agent import NodeHealthAgent


def _agente(
    tmp_path,
):
    agente = object.__new__(NodeHealthAgent)

    agente.caminho_estado = tmp_path / "estado_atual.json"

    agente.intervalo_segundos = 300

    return agente


def _preparar(
    monkeypatch,
    *,
    analisar_qualidade=None,
    salvar_qualidade=None,
    gerar_sintese=None,
    salvar_sintese=None,
):
    monkeypatch.setattr(
        node_agent_module,
        "analisar_qualidade_temporal_interpretacoes_node",
        (
            analisar_qualidade
            if analisar_qualidade is not None
            else lambda *args, **kwargs: "QUALIDADE"
        ),
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_qualidade_temporal_interpretacoes_node",
        (
            salvar_qualidade
            if salvar_qualidade is not None
            else lambda qualidade, caminho: Path(caminho)
        ),
    )

    monkeypatch.setattr(
        node_agent_module,
        "gerar_sintese_evidencias_interpretacoes_node",
        (gerar_sintese if gerar_sintese is not None else lambda *args: "SINTESE"),
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_sintese_evidencias_interpretacoes_node",
        (salvar_sintese if salvar_sintese is not None else lambda sintese, caminho: Path(caminho)),
    )


def test_v130_sintese_roda_depois_da_qualidade_salva(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def analisar_qualidade(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        chamadas.append("analisar_qualidade")

        return "QUALIDADE"

    def salvar_qualidade(
        qualidade,
        caminho,
    ):
        del qualidade
        del caminho

        chamadas.append("salvar_qualidade")

        return Path("qualidade.json")

    def gerar_sintese(
        *args,
    ):
        del args

        chamadas.append("gerar_sintese")

        return "SINTESE"

    def salvar_sintese(
        sintese,
        caminho,
    ):
        del sintese
        del caminho

        chamadas.append("salvar_sintese")

        return Path("sintese.json")

    _preparar(
        monkeypatch,
        analisar_qualidade=analisar_qualidade,
        salvar_qualidade=salvar_qualidade,
        gerar_sintese=gerar_sintese,
        salvar_sintese=salvar_sintese,
    )

    _agente(tmp_path)._atualizar_qualidade_temporal_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json"
    )

    assert chamadas == [
        "analisar_qualidade",
        "salvar_qualidade",
        "gerar_sintese",
        "salvar_sintese",
    ]


def test_v130_sintese_recebe_caminhos_corretos(
    tmp_path,
    monkeypatch,
):
    recebido = {}

    def analisar(
        caminho_resumo,
        diretorio_historico,
        *,
        cadencia_nominal_segundos,
    ):
        recebido["resumo_qualidade"] = Path(caminho_resumo)

        recebido["historico"] = Path(diretorio_historico)

        recebido["cadencia"] = cadencia_nominal_segundos

        return "QUALIDADE"

    def salvar_qualidade(
        qualidade,
        caminho,
    ):
        del qualidade

        recebido["qualidade"] = Path(caminho)

        return Path(caminho)

    def gerar_sintese(
        caminho_resumo,
        caminho_qualidade,
    ):
        recebido["resumo_sintese"] = Path(caminho_resumo)

        recebido["qualidade_sintese"] = Path(caminho_qualidade)

        return "SINTESE"

    def salvar_sintese(
        sintese,
        caminho,
    ):
        del sintese

        recebido["sintese"] = Path(caminho)

        return Path(caminho)

    _preparar(
        monkeypatch,
        analisar_qualidade=analisar,
        salvar_qualidade=salvar_qualidade,
        gerar_sintese=gerar_sintese,
        salvar_sintese=salvar_sintese,
    )

    _agente(tmp_path)._atualizar_qualidade_temporal_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json"
    )

    assert recebido == {
        "resumo_qualidade": (tmp_path / "resumo_temporal_interpretacoes_atual.json"),
        "historico": (tmp_path / "historico_interpretacoes"),
        "cadencia": 300,
        "qualidade": (tmp_path / "qualidade_temporal_interpretacoes_atual.json"),
        "resumo_sintese": (tmp_path / "resumo_temporal_interpretacoes_atual.json"),
        "qualidade_sintese": (tmp_path / "qualidade_temporal_interpretacoes_atual.json"),
        "sintese": (tmp_path / "sintese_evidencias_interpretacoes_atual.json"),
    }


def test_v130_falha_analisar_qualidade_suprime_sintese(
    tmp_path,
    monkeypatch,
):
    def analisar_falha(
        *args,
        **kwargs,
    ):
        del args
        del kwargs

        raise RuntimeError("falha proposital")

    def sintese_proibida(
        *args,
    ):
        del args

        raise AssertionError("Sintese nao deveria rodar.")

    _preparar(
        monkeypatch,
        analisar_qualidade=analisar_falha,
        gerar_sintese=sintese_proibida,
    )

    _agente(tmp_path)._atualizar_qualidade_temporal_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json"
    )


def test_v130_falha_salvar_qualidade_suprime_sintese(
    tmp_path,
    monkeypatch,
):
    def salvar_qualidade_falha(
        qualidade,
        caminho,
    ):
        del qualidade
        del caminho

        raise RuntimeError("falha proposital")

    def sintese_proibida(
        *args,
    ):
        del args

        raise AssertionError("Sintese nao deveria rodar.")

    _preparar(
        monkeypatch,
        salvar_qualidade=salvar_qualidade_falha,
        gerar_sintese=sintese_proibida,
    )

    _agente(tmp_path)._atualizar_qualidade_temporal_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json"
    )


def test_v130_falha_gerar_sintese_e_isolada(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def gerar_falha(
        *args,
    ):
        del args

        chamadas.append("gerar")

        raise RuntimeError("falha proposital")

    _preparar(
        monkeypatch,
        gerar_sintese=gerar_falha,
    )

    _agente(tmp_path)._atualizar_qualidade_temporal_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json"
    )

    assert chamadas == ["gerar"]


def test_v130_falha_salvar_sintese_e_isolada(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def salvar_falha(
        sintese,
        caminho,
    ):
        del sintese
        del caminho

        chamadas.append("salvar")

        raise RuntimeError("falha proposital")

    _preparar(
        monkeypatch,
        salvar_sintese=salvar_falha,
    )

    _agente(tmp_path)._atualizar_qualidade_temporal_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json"
    )

    assert chamadas == ["salvar"]


def test_v130_sintese_so_roda_depois_da_qualidade_salva(
    tmp_path,
    monkeypatch,
):
    qualidade_salva = {"valor": False}

    def salvar_qualidade(
        qualidade,
        caminho,
    ):
        del qualidade

        qualidade_salva["valor"] = True

        return Path(caminho)

    def gerar_sintese(
        *args,
    ):
        del args

        assert qualidade_salva["valor"] is True

        return "SINTESE"

    _preparar(
        monkeypatch,
        salvar_qualidade=salvar_qualidade,
        gerar_sintese=gerar_sintese,
    )

    _agente(tmp_path)._atualizar_qualidade_temporal_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json"
    )
