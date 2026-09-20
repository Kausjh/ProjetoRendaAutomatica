# 63.8738, -149.7525

from __future__ import annotations

from types import SimpleNamespace

import services.mission_runtime as mission_runtime
from models.mission_community import (
    ResultadoWiringMissaoCommunity,
)
from services.mission_community_approved_wiring import (
    MissionCommunityApprovedWiring,
)
from services.mission_community_live_settlement_wiring import (
    MissionCommunityLiveSettlementWiring,
)


def _mission_result(
    *,
    falhas=(),
    recompensas_criadas=0,
):
    return ResultadoWiringMissaoCommunity(
        descoberta_id="dsc_1",
        status=("success" if not falhas else "error"),
        eventos_criados=3,
        eventos_idempotentes=0,
        eventos_completados=0,
        missoes_concluidas_agora=(1 if recompensas_criadas else 0),
        recompensas_criadas=(recompensas_criadas),
        falhas=tuple(falhas),
    )


class MissionWiringFake:
    def __init__(self, resultado):
        self.resultado = resultado
        self.chamadas = 0

    def processar_aprovacao(self, **kwargs):
        self.chamadas += 1
        self.kwargs = kwargs
        return self.resultado


class SettlementFake:
    def __init__(self, resultado):
        self.resultado = resultado
        self.chamadas = 0

    def liquidar_pendentes(
        self,
        *,
        limite,
    ):
        self.chamadas += 1
        self.limite = limite
        return self.resultado


def _settlement_result(
    *,
    encontrados=0,
    falhas=(),
):
    return SimpleNamespace(
        recompensas_encontradas=encontrados,
        eventos_criados=0,
        eventos_idempotentes=0,
        recompensas_marcadas=0,
        recompensas_idempotentes=0,
        falhas=tuple(falhas),
    )


def test_live_settlement_roda_depois_da_missao():
    mission = MissionWiringFake(
        _mission_result(
            recompensas_criadas=1,
        )
    )

    settlement = SettlementFake(
        _settlement_result(
            encontrados=1,
        )
    )

    wiring = MissionCommunityLiveSettlementWiring(
        mission_wiring=mission,
        settlement_service=settlement,
    )

    resultado = wiring.processar_aprovacao(
        descoberta_id="dsc_1",
        conta_id="usr_1",
        status="approved",
        ocorrido_em="2026-09-20T18:00:00+00:00",
    )

    assert resultado.sucesso is True
    assert resultado.falhas == ()

    assert mission.chamadas == 1
    assert settlement.chamadas == 1
    assert settlement.limite == 100


def test_live_settlement_varre_pending_mesmo_sem_reward_novo():
    mission = MissionWiringFake(
        _mission_result(
            recompensas_criadas=0,
        )
    )

    settlement = SettlementFake(
        _settlement_result(
            encontrados=1,
        )
    )

    wiring = MissionCommunityLiveSettlementWiring(
        mission_wiring=mission,
        settlement_service=settlement,
    )

    resultado = wiring.processar_aprovacao(
        descoberta_id="dsc_2",
        conta_id="usr_1",
        status="approved",
        ocorrido_em="2026-09-20T18:01:00+00:00",
    )

    assert resultado.sucesso is True
    assert settlement.chamadas == 1
    assert resultado.settlement_result is settlement.resultado


def test_falha_da_missao_nao_impede_sweep_settlement():
    mission = MissionWiringFake(
        _mission_result(
            falhas=("falha_missao",),
        )
    )

    settlement = SettlementFake(_settlement_result())

    wiring = MissionCommunityLiveSettlementWiring(
        mission_wiring=mission,
        settlement_service=settlement,
    )

    resultado = wiring.processar_aprovacao(
        descoberta_id="dsc_3",
        conta_id="usr_1",
        status="approved",
        ocorrido_em="2026-09-20T18:02:00+00:00",
    )

    assert resultado.sucesso is False
    assert resultado.falhas == ("mission:falha_missao",)

    assert settlement.chamadas == 1


def test_falha_settlement_fica_exposta_sem_raise():
    mission = MissionWiringFake(_mission_result())

    settlement = SettlementFake(
        _settlement_result(
            falhas=("reward_1:erro",),
        )
    )

    wiring = MissionCommunityLiveSettlementWiring(
        mission_wiring=mission,
        settlement_service=settlement,
    )

    resultado = wiring.processar_aprovacao(
        descoberta_id="dsc_4",
        conta_id="usr_1",
        status="approved",
        ocorrido_em="2026-09-20T18:03:00+00:00",
    )

    assert resultado.sucesso is False

    assert resultado.falhas == ("settlement:reward_1:erro",)


def test_flag_live_default_off(monkeypatch):
    monkeypatch.delenv(
        mission_runtime.LIVE_REWARD_SETTLEMENT_FLAG,
        raising=False,
    )

    assert mission_runtime._live_reward_settlement_ativo() is False


def test_flag_live_aceita_true(monkeypatch):
    monkeypatch.setenv(
        mission_runtime.LIVE_REWARD_SETTLEMENT_FLAG,
        "true",
    )

    assert mission_runtime._live_reward_settlement_ativo() is True


def test_factory_flag_off_preserva_wiring_original(
    monkeypatch,
):
    base = object()
    service = object()

    monkeypatch.setattr(
        mission_runtime,
        "_criar_service_e_wiring",
        lambda **kwargs: (
            service,
            base,
        ),
    )

    monkeypatch.setenv(
        mission_runtime.LIVE_REWARD_SETTLEMENT_FLAG,
        "0",
    )

    resultado = mission_runtime.criar_wiring_missoes_live(
        caminho_banco="qualquer.sqlite3",
    )

    assert resultado is base


def test_factory_flag_on_compoe_live_settlement(
    monkeypatch,
):
    base = MissionWiringFake(_mission_result())
    service = object()
    settlement = object()

    monkeypatch.setattr(
        mission_runtime,
        "_criar_service_e_wiring",
        lambda **kwargs: (
            service,
            base,
        ),
    )

    monkeypatch.setattr(
        mission_runtime,
        "criar_componentes_reward_settlement",
        lambda **kwargs: (
            settlement,
            object(),
        ),
    )

    monkeypatch.setenv(
        mission_runtime.LIVE_REWARD_SETTLEMENT_FLAG,
        "1",
    )

    resultado = mission_runtime.criar_wiring_missoes_live(
        caminho_banco="qualquer.sqlite3",
    )

    assert isinstance(
        resultado,
        MissionCommunityLiveSettlementWiring,
    )

    assert resultado.mission_wiring is base
    assert resultado.settlement_service is settlement


def test_factory_settlement_indisponivel_preserva_missoes(
    monkeypatch,
):
    base = MissionWiringFake(_mission_result())
    service = object()

    monkeypatch.setattr(
        mission_runtime,
        "_criar_service_e_wiring",
        lambda **kwargs: (
            service,
            base,
        ),
    )

    def falhar(**kwargs):
        raise RuntimeError("settlement indisponivel")

    monkeypatch.setattr(
        mission_runtime,
        "criar_componentes_reward_settlement",
        falhar,
    )

    monkeypatch.setenv(
        mission_runtime.LIVE_REWARD_SETTLEMENT_FLAG,
        "1",
    )

    resultado = mission_runtime.criar_wiring_missoes_live(
        caminho_banco="qualquer.sqlite3",
    )

    assert resultado is base


def test_factory_publico_ainda_aceita_wiring_original():
    assert MissionCommunityApprovedWiring is not None
