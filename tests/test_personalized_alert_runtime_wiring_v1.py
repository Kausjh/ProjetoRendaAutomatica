from __future__ import annotations

from pathlib import Path

from models.alert_engine import EventoAlertEngine, ResultadoAlertEngine
from repositories.personalized_alert_match_repository import (
    PersonalizedAlertMatchRepository,
)
from repositories.personalized_notification_outbox_repository import (
    PersonalizedNotificationOutboxRepository,
)
from repositories.user_identity_repository import UserIdentityRepository
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)
from services.personalized_alert_matching_service import PersonalizedAlertMatchingService
from services.personalized_alert_runtime_service import PersonalizedAlertRuntimeService
from services.personalized_notification_outbox_service import (
    PersonalizedNotificationOutboxService,
)
from services.user_identity_service import UserIdentityService
from services.user_personalization_service import UserPersonalizationService


def _resultado_alert_engine() -> ResultadoAlertEngine:
    return ResultadoAlertEngine(
        status="processado",
        processado=True,
        baseline_inicializada=False,
        alertas_gerados=1,
        tipos_gerados=("mudanca_preco",),
        chave_canonica="gpu_teste",
        marketplace="mercado_livre",
        identificador="MLB123",
        motivo="teste",
        eventos=(
            EventoAlertEngine(
                fingerprint="fingerprint-estavel-001",
                tipo="mudanca_preco",
                chave_canonica="gpu_teste",
                nome_canonico="GPU Teste",
                marketplace="mercado_livre",
                identificador="MLB123",
                preco_atual=900.0,
                preco_anterior=1000.0,
                criado_em="2026-09-15T15:00:00+00:00",
            ),
        ),
    )


def _contexto(tmp_path: Path):
    banco = tmp_path / "user_identity.sqlite3"

    identity_repo = UserIdentityRepository(banco)
    identity_service = UserIdentityService(identity_repo)

    personalization_repo = UserPersonalizationRepository(banco)
    personalization_service = UserPersonalizationService(
        personalization_repo,
        identity_repo,
    )

    match_repo = PersonalizedAlertMatchRepository(banco)
    matching_service = PersonalizedAlertMatchingService(
        personalization_repository=personalization_repo,
        match_repository=match_repo,
    )

    outbox_repo = PersonalizedNotificationOutboxRepository(banco)
    outbox_service = PersonalizedNotificationOutboxService(outbox_repo)

    runtime = PersonalizedAlertRuntimeService(
        matching_service=matching_service,
        outbox_service=outbox_service,
    )

    conta = identity_service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )

    personalization_service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
        notificar_queda_preco=False,
    )

    return runtime, match_repo, outbox_repo, conta


def test_alert_engine_vira_match_e_outbox(tmp_path: Path):
    runtime, match_repo, outbox_repo, conta = _contexto(tmp_path)

    resultado = runtime.processar(_resultado_alert_engine())

    assert resultado.eventos_processados == 1
    assert resultado.correspondencias == 1
    assert resultado.itens_outbox_criados == 1

    matches = match_repo.listar_por_conta(conta.id)
    assert len(matches) == 1
    assert matches[0].canonical_key == "gpu_teste"

    itens = outbox_repo.listar_por_conta(conta.id)
    assert len(itens) == 1
    assert itens[0].status == "pending"
    assert itens[0].tentativas == 0


def test_reprocessamento_nao_duplica_match_nem_outbox(tmp_path: Path):
    runtime, match_repo, outbox_repo, conta = _contexto(tmp_path)
    resultado_alert = _resultado_alert_engine()

    primeiro = runtime.processar(resultado_alert)
    segundo = runtime.processar(resultado_alert)

    assert primeiro.itens_outbox_criados == 1
    assert segundo.itens_outbox_criados == 0
    assert len(match_repo.listar_por_conta(conta.id)) == 1
    assert len(outbox_repo.listar_por_conta(conta.id)) == 1


def test_sem_correspondencia_nao_cria_outbox(tmp_path: Path):
    banco = tmp_path / "user_identity.sqlite3"

    identity_repo = UserIdentityRepository(banco)
    UserIdentityService(identity_repo).criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )

    personalization_repo = UserPersonalizationRepository(banco)
    matching_service = PersonalizedAlertMatchingService(
        personalization_repository=personalization_repo,
        match_repository=PersonalizedAlertMatchRepository(banco),
    )
    outbox_repo = PersonalizedNotificationOutboxRepository(banco)
    runtime = PersonalizedAlertRuntimeService(
        matching_service=matching_service,
        outbox_service=PersonalizedNotificationOutboxService(outbox_repo),
    )

    resultado = runtime.processar(_resultado_alert_engine())

    assert resultado.eventos_processados == 1
    assert resultado.correspondencias == 0
    assert resultado.itens_outbox_criados == 0
