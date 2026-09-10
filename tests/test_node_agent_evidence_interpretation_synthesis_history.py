from pathlib import Path

import services.infra.node_agent as node_agent_module
from services.infra.node_agent import NodeHealthAgent


def _agente(
    tmp_path,
):
    agente = object.__new__(NodeHealthAgent)

    agente.caminho_estado = tmp_path / "estado_atual.json"

    return agente


def _preparar(
    monkeypatch,
    *,
    gerar_sintese=None,
    salvar_sintese=None,
    persistir_historico=None,
):
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

    monkeypatch.setattr(
        node_agent_module,
        "persistir_sintese_evidencias_interpretacoes_node",
        (persistir_historico if persistir_historico is not None else lambda *args: "RESULTADO"),
    )


def test_v132_historico_roda_depois_da_sintese_salva(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def gerar(
        *args,
    ):
        del args

        chamadas.append("gerar")

        return "SINTESE"

    def salvar(
        sintese,
        caminho,
    ):
        del sintese
        del caminho

        chamadas.append("salvar")

        return Path("sintese.json")

    def persistir(
        *args,
    ):
        del args

        chamadas.append("persistir")

        return "RESULTADO"

    _preparar(
        monkeypatch,
        gerar_sintese=gerar,
        salvar_sintese=salvar,
        persistir_historico=persistir,
    )

    _agente(tmp_path)._atualizar_sintese_evidencias_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json",
        tmp_path / "qualidade_temporal_interpretacoes_atual.json",
    )

    assert chamadas == [
        "gerar",
        "salvar",
        "persistir",
    ]


def test_v132_historico_recebe_caminhos_corretos(
    tmp_path,
    monkeypatch,
):
    recebido = {}

    def persistir(
        caminho_sintese,
        diretorio_historico,
    ):
        recebido["sintese"] = Path(caminho_sintese)

        recebido["historico"] = Path(diretorio_historico)

        return "RESULTADO"

    _preparar(
        monkeypatch,
        persistir_historico=persistir,
    )

    _agente(tmp_path)._atualizar_sintese_evidencias_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json",
        tmp_path / "qualidade_temporal_interpretacoes_atual.json",
    )

    assert recebido == {
        "sintese": (tmp_path / "sintese_evidencias_interpretacoes_atual.json"),
        "historico": (tmp_path / "historico_sinteses_interpretacoes"),
    }


def test_v132_falha_gerar_sintese_suprime_historico(
    tmp_path,
    monkeypatch,
):
    def gerar_falha(
        *args,
    ):
        del args

        raise RuntimeError("falha proposital")

    def historico_proibido(
        *args,
    ):
        del args

        raise AssertionError("Historico nao deveria rodar.")

    _preparar(
        monkeypatch,
        gerar_sintese=gerar_falha,
        persistir_historico=historico_proibido,
    )

    _agente(tmp_path)._atualizar_sintese_evidencias_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json",
        tmp_path / "qualidade_temporal_interpretacoes_atual.json",
    )


def test_v132_falha_salvar_sintese_suprime_historico(
    tmp_path,
    monkeypatch,
):
    def salvar_falha(
        sintese,
        caminho,
    ):
        del sintese
        del caminho

        raise RuntimeError("falha proposital")

    def historico_proibido(
        *args,
    ):
        del args

        raise AssertionError("Historico nao deveria rodar.")

    _preparar(
        monkeypatch,
        salvar_sintese=salvar_falha,
        persistir_historico=historico_proibido,
    )

    _agente(tmp_path)._atualizar_sintese_evidencias_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json",
        tmp_path / "qualidade_temporal_interpretacoes_atual.json",
    )


def test_v132_falha_historico_e_isolada(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def persistir_falha(
        *args,
    ):
        del args

        chamadas.append("persistir")

        raise RuntimeError("falha proposital")

    _preparar(
        monkeypatch,
        persistir_historico=persistir_falha,
    )

    _agente(tmp_path)._atualizar_sintese_evidencias_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json",
        tmp_path / "qualidade_temporal_interpretacoes_atual.json",
    )

    assert chamadas == ["persistir"]


def test_v132_historico_so_roda_depois_da_sintese_salva(
    tmp_path,
    monkeypatch,
):
    sintese_salva = {"valor": False}

    def salvar(
        sintese,
        caminho,
    ):
        del sintese

        sintese_salva["valor"] = True

        return Path(caminho)

    def persistir(
        *args,
    ):
        del args

        assert sintese_salva["valor"] is True

        return "RESULTADO"

    _preparar(
        monkeypatch,
        salvar_sintese=salvar,
        persistir_historico=persistir,
    )

    _agente(tmp_path)._atualizar_sintese_evidencias_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json",
        tmp_path / "qualidade_temporal_interpretacoes_atual.json",
    )


def test_v132_persistencia_nao_altera_resultado_da_sintese(
    tmp_path,
    monkeypatch,
):
    gerada = {"valor": False}

    salva = {"valor": False}

    def gerar(
        *args,
    ):
        del args

        gerada["valor"] = True

        return "SINTESE"

    def salvar(
        sintese,
        caminho,
    ):
        assert sintese == "SINTESE"

        salva["valor"] = True

        return Path(caminho)

    def persistir(
        *args,
    ):
        del args

        assert gerada["valor"] is True
        assert salva["valor"] is True

        return "RESULTADO"

    _preparar(
        monkeypatch,
        gerar_sintese=gerar,
        salvar_sintese=salvar,
        persistir_historico=persistir,
    )

    resultado = _agente(tmp_path)._atualizar_sintese_evidencias_interpretacoes(
        tmp_path / "resumo_temporal_interpretacoes_atual.json",
        tmp_path / "qualidade_temporal_interpretacoes_atual.json",
    )

    assert resultado is None
