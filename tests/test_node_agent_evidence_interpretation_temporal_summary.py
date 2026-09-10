from pathlib import Path

import services.infra.node_agent as node_agent_module
from services.infra.node_agent import NodeHealthAgent


def _agente(tmp_path):
    agente = object.__new__(NodeHealthAgent)

    agente.caminho_estado = tmp_path / "estado_atual.json"

    return agente


def _preparar(
    monkeypatch,
    *,
    analisar=None,
    salvar_analise=None,
    gerar_resumo=None,
    salvar_resumo=None,
):
    monkeypatch.setattr(
        node_agent_module,
        "analisar_historico_interpretacoes_node",
        (analisar if analisar is not None else lambda diretorio: "ANALISE"),
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_analise_historico_interpretacoes_node",
        (salvar_analise if salvar_analise is not None else lambda analise, caminho: Path(caminho)),
    )

    monkeypatch.setattr(
        node_agent_module,
        "gerar_resumo_temporal_interpretacoes_node",
        (gerar_resumo if gerar_resumo is not None else lambda *args: "RESUMO"),
    )

    monkeypatch.setattr(
        node_agent_module,
        "salvar_resumo_temporal_interpretacoes_node",
        (salvar_resumo if salvar_resumo is not None else lambda resumo, caminho: Path(caminho)),
    )


def test_v126_ordem_analise_depois_resumo(
    tmp_path,
    monkeypatch,
):
    chamadas = []

    def analisar(diretorio):
        del diretorio
        chamadas.append("analisar")
        return "ANALISE"

    def salvar_analise(analise, caminho):
        del analise
        del caminho
        chamadas.append("salvar_analise")
        return Path("analise.json")

    def gerar_resumo(*args):
        del args
        chamadas.append("gerar_resumo")
        return "RESUMO"

    def salvar_resumo(resumo, caminho):
        del resumo
        del caminho
        chamadas.append("salvar_resumo")
        return Path("resumo.json")

    _preparar(
        monkeypatch,
        analisar=analisar,
        salvar_analise=salvar_analise,
        gerar_resumo=gerar_resumo,
        salvar_resumo=salvar_resumo,
    )

    _agente(tmp_path)._atualizar_analise_historico_interpretacoes(
        tmp_path / "historico_interpretacoes"
    )

    assert chamadas == [
        "analisar",
        "salvar_analise",
        "gerar_resumo",
        "salvar_resumo",
    ]


def test_v126_caminhos_corretos(
    tmp_path,
    monkeypatch,
):
    recebido = {}

    def analisar(diretorio):
        recebido["historico"] = Path(diretorio)
        return "ANALISE"

    def salvar_analise(analise, caminho):
        del analise
        recebido["analise"] = Path(caminho)
        return Path(caminho)

    def gerar_resumo(
        caminho_estado,
        caminho_analise,
    ):
        recebido["estado"] = Path(caminho_estado)
        recebido["analise_resumo"] = Path(caminho_analise)
        return "RESUMO"

    def salvar_resumo(resumo, caminho):
        del resumo
        recebido["resumo"] = Path(caminho)
        return Path(caminho)

    _preparar(
        monkeypatch,
        analisar=analisar,
        salvar_analise=salvar_analise,
        gerar_resumo=gerar_resumo,
        salvar_resumo=salvar_resumo,
    )

    _agente(tmp_path)._atualizar_analise_historico_interpretacoes(
        tmp_path / "historico_interpretacoes"
    )

    assert recebido == {
        "historico": (tmp_path / "historico_interpretacoes"),
        "analise": (tmp_path / "analise_historico_interpretacoes_atual.json"),
        "estado": (tmp_path / "interpretacao_estado_atual.json"),
        "analise_resumo": (tmp_path / "analise_historico_interpretacoes_atual.json"),
        "resumo": (tmp_path / "resumo_temporal_interpretacoes_atual.json"),
    }


def test_v126_falha_analise_suprime_resumo(
    tmp_path,
    monkeypatch,
):
    def analisar(diretorio):
        del diretorio
        raise RuntimeError("falha")

    def resumo_proibido(*args):
        del args
        raise AssertionError("Resumo nao deveria rodar.")

    _preparar(
        monkeypatch,
        analisar=analisar,
        gerar_resumo=resumo_proibido,
    )

    _agente(tmp_path)._atualizar_analise_historico_interpretacoes(
        tmp_path / "historico_interpretacoes"
    )


def test_v126_falha_salvar_analise_suprime_resumo(
    tmp_path,
    monkeypatch,
):
    def salvar_analise(analise, caminho):
        del analise
        del caminho
        raise RuntimeError("falha")

    def resumo_proibido(*args):
        del args
        raise AssertionError("Resumo nao deveria rodar.")

    _preparar(
        monkeypatch,
        salvar_analise=salvar_analise,
        gerar_resumo=resumo_proibido,
    )

    _agente(tmp_path)._atualizar_analise_historico_interpretacoes(
        tmp_path / "historico_interpretacoes"
    )


def test_v126_falha_gerar_resumo_e_isolada(
    tmp_path,
    monkeypatch,
):
    def gerar_resumo(*args):
        del args
        raise RuntimeError("falha")

    _preparar(
        monkeypatch,
        gerar_resumo=gerar_resumo,
    )

    _agente(tmp_path)._atualizar_analise_historico_interpretacoes(
        tmp_path / "historico_interpretacoes"
    )


def test_v126_falha_salvar_resumo_e_isolada(
    tmp_path,
    monkeypatch,
):
    def salvar_resumo(resumo, caminho):
        del resumo
        del caminho
        raise RuntimeError("falha")

    _preparar(
        monkeypatch,
        salvar_resumo=salvar_resumo,
    )

    _agente(tmp_path)._atualizar_analise_historico_interpretacoes(
        tmp_path / "historico_interpretacoes"
    )


def test_v126_resumo_so_roda_apos_analise_salva(
    tmp_path,
    monkeypatch,
):
    analise_salva = {"valor": False}

    def salvar_analise(analise, caminho):
        del analise
        analise_salva["valor"] = True
        return Path(caminho)

    def gerar_resumo(*args):
        del args
        assert analise_salva["valor"] is True
        return "RESUMO"

    _preparar(
        monkeypatch,
        salvar_analise=salvar_analise,
        gerar_resumo=gerar_resumo,
    )

    _agente(tmp_path)._atualizar_analise_historico_interpretacoes(
        tmp_path / "historico_interpretacoes"
    )
