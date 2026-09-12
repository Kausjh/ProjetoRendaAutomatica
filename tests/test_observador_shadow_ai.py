from __future__ import annotations

from datetime import UTC, datetime, timedelta

from models.inteligencia_ai import SolicitacaoInteligenciaAI
from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.observador_shadow_ai import (
    CUSTO_ENTRADA_USD_POR_MILHAO,
    CUSTO_SAIDA_USD_POR_MILHAO,
    MODELO_REFERENCIA_SHADOW_AI,
    ObservadorShadowAI,
)


def _solicitacao_classificador() -> SolicitacaoInteligenciaAI:
    return SolicitacaoInteligenciaAI(
        tarefa="desambiguar_categoria_produto",
        contexto={
            "titulo": "Ryzen NVMe",
            "categorias_candidatas": [
                "Processador",
                "Armazenamento",
            ],
        },
    )


def _solicitacao_curadoria() -> SolicitacaoInteligenciaAI:
    return SolicitacaoInteligenciaAI(
        tarefa="interpretar_incerteza_editorial",
        contexto={
            "titulo": "RTX 4060",
            "categoria": "Placa de video",
            "sinais_deterministicos": [
                "confianca_normalizacao_abaixo_de_90",
            ],
        },
    )


def test_shadow_persiste_agregados_entre_instancias(tmp_path) -> None:
    caminho = tmp_path / "controle.sqlite3"
    agora = datetime(2026, 9, 12, 15, 0, tzinfo=UTC)
    repo = ControleAdministrativoRepository(str(caminho))
    observador = ObservadorShadowAI(
        repositorio=repo,
        agora=lambda: agora,
    )

    assert observador.registrar_gate(
        consumidor="classificador",
        solicitacao=_solicitacao_classificador(),
    )

    outro_processo = ObservadorShadowAI(
        repositorio=ControleAdministrativoRepository(str(caminho)),
        agora=lambda: agora,
    )
    snapshot = outro_processo.obter_snapshot()

    assert snapshot["eventos_total"] == 1
    assert snapshot["por_consumidor"]["classificador"]["eventos"] == 1
    assert snapshot["por_consumidor"]["curadoria"]["eventos"] == 0
    assert snapshot["estimativas"]["tokens_total"] > 0
    assert snapshot["estimativas"]["custo_usd"] > 0
    assert snapshot["modelo_referencia"] == MODELO_REFERENCIA_SHADOW_AI


def test_shadow_separa_consumidores_e_dias(tmp_path) -> None:
    instante = {"valor": datetime(2026, 9, 12, 15, 0, tzinfo=UTC)}
    observador = ObservadorShadowAI(
        repositorio=ControleAdministrativoRepository(str(tmp_path / "controle.sqlite3")),
        agora=lambda: instante["valor"],
    )

    assert observador.registrar_gate(
        consumidor="classificador",
        solicitacao=_solicitacao_classificador(),
    )

    instante["valor"] = instante["valor"] + timedelta(days=1)

    assert observador.registrar_gate(
        consumidor="curadoria",
        solicitacao=_solicitacao_curadoria(),
    )

    snapshot = observador.obter_snapshot()
    assert snapshot["eventos_total"] == 2
    assert snapshot["por_consumidor"]["classificador"]["eventos"] == 1
    assert snapshot["por_consumidor"]["curadoria"]["eventos"] == 1
    assert len(snapshot["por_dia"]) == 2


def test_shadow_para_automaticamente_apos_sete_dias(tmp_path) -> None:
    instante = {"valor": datetime(2026, 9, 12, 15, 0, tzinfo=UTC)}
    observador = ObservadorShadowAI(
        repositorio=ControleAdministrativoRepository(str(tmp_path / "controle.sqlite3")),
        agora=lambda: instante["valor"],
    )

    assert observador.registrar_gate(
        consumidor="classificador",
        solicitacao=_solicitacao_classificador(),
    )

    instante["valor"] = instante["valor"] + timedelta(days=7)

    assert (
        observador.registrar_gate(
            consumidor="curadoria",
            solicitacao=_solicitacao_curadoria(),
        )
        is False
    )

    snapshot = observador.obter_snapshot()
    assert snapshot["concluido"] is True
    assert snapshot["eventos_total"] == 1


def test_shadow_estimativa_custo_e_explicita(tmp_path) -> None:
    observador = ObservadorShadowAI(
        repositorio=ControleAdministrativoRepository(str(tmp_path / "controle.sqlite3")),
        agora=lambda: datetime(2026, 9, 12, 15, 0, tzinfo=UTC),
    )

    observador.registrar_gate(
        consumidor="curadoria",
        solicitacao=_solicitacao_curadoria(),
    )

    snapshot = observador.obter_snapshot()
    estimativas = snapshot["estimativas"]
    assert estimativas["tokens_entrada"] >= 180
    assert estimativas["tokens_saida"] == 120

    esperado = round(
        (estimativas["tokens_entrada"] * CUSTO_ENTRADA_USD_POR_MILHAO / 1_000_000)
        + (estimativas["tokens_saida"] * CUSTO_SAIDA_USD_POR_MILHAO / 1_000_000),
        10,
    )
    assert estimativas["custo_usd"] == esperado


def test_shadow_nao_persiste_payload_ou_titulo(tmp_path) -> None:
    caminho = tmp_path / "controle.sqlite3"
    observador = ObservadorShadowAI(
        repositorio=ControleAdministrativoRepository(str(caminho)),
        agora=lambda: datetime(2026, 9, 12, 15, 0, tzinfo=UTC),
    )

    observador.registrar_gate(
        consumidor="classificador",
        solicitacao=_solicitacao_classificador(),
    )

    bruto = ControleAdministrativoRepository(str(caminho)).obter_estado("shadow_ai_v1")
    assert bruto is not None
    assert "Ryzen NVMe" not in bruto
    assert "categorias_candidatas" not in bruto
