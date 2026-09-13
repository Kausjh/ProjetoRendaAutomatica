from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from models.personalized_alert_match import EventoAlertaPersonalizavel
from repositories.personalized_alert_match_repository import (
    PersonalizedAlertMatchRepository,
)
from repositories.user_identity_repository import UserIdentityRepository
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)
from services.personalized_alert_matching_service import (
    PersonalizedAlertMatchingService,
)
from services.user_identity_service import UserIdentityService
from services.user_personalization_service import UserPersonalizationService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "personalized_alert_matching_v1.json"
DOC = ROOT / "docs" / "15-alertas-personalizados-matching.md"
API_SERVER = ROOT / "services" / "api_aplicacao" / "servidor.py"


@pytest.fixture
def contexto(tmp_path: Path):
    banco = tmp_path / "user_identity.sqlite3"

    identity_repo = UserIdentityRepository(banco)
    identity_service = UserIdentityService(identity_repo)

    personalization_repo = UserPersonalizationRepository(banco)
    personalization_service = UserPersonalizationService(
        personalization_repo,
        identity_repo,
    )

    match_repo = PersonalizedAlertMatchRepository(banco)
    matching = PersonalizedAlertMatchingService(
        personalization_repository=personalization_repo,
        match_repository=match_repo,
    )

    conta = identity_service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )

    return (
        banco,
        identity_service,
        personalization_service,
        personalization_repo,
        match_repo,
        matching,
        conta,
    )


def evento(
    *,
    evento_id: str = "evt_1",
    canonical_key: str = "gpu_teste",
    tipo: str = "mudanca_preco",
    atual: str = "900.00",
    anterior: str | None = "1000.00",
    marketplace: str | None = "mercado_livre",
) -> EventoAlertaPersonalizavel:
    return EventoAlertaPersonalizavel(
        evento_id=evento_id,
        canonical_key=canonical_key,
        tipo_evento=tipo,
        preco_atual=Decimal(atual),
        preco_anterior=(Decimal(anterior) if anterior is not None else None),
        marketplace=marketplace,
        ocorrido_em="2026-09-13T12:00:00+00:00",
    )


def test_contract_matching_sem_delivery():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["schema"] == ("projeto-renda-automatica.personalized-alert-matching")
    assert data["matching_version"] == 1
    assert data["network_exposure"] is False
    assert data["delivery_enabled"] is False


def test_contract_preserva_fronteiras():
    b = json.loads(CONTRACT.read_text(encoding="utf-8"))["boundaries"]
    assert b["application_api_v1_remains_read_only"] is True
    assert b["new_http_routes"] is False
    assert b["push_delivery"] is False
    assert b["telegram_delivery"] is False
    assert b["email_delivery"] is False
    assert b["good_deal_classification"] is False


def test_preco_alvo_atingido_gera_match(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
        notificar_queda_preco=False,
    )

    matches = matching.processar_evento(evento(atual="900.00"))

    assert len(matches) == 1
    assert matches[0].motivos == ("target_price_reached",)


def test_preco_acima_alvo_sem_queda_configurada_nao_gera(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="850.00",
        notificar_queda_preco=False,
    )

    assert matching.processar_evento(evento(atual="900.00")) == []


def test_queda_direcional_gera_match(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        notificar_queda_preco=True,
    )

    matches = matching.processar_evento(evento(atual="900.00", anterior="1000.00"))

    assert len(matches) == 1
    assert matches[0].motivos == ("price_drop_detected",)


def test_aumento_de_preco_nao_e_queda(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        notificar_queda_preco=True,
    )

    assert matching.processar_evento(evento(atual="1100.00", anterior="1000.00")) == []


def test_mudanca_sem_preco_anterior_falha_fechada(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        notificar_queda_preco=True,
    )

    assert matching.processar_evento(evento(anterior=None)) == []


def test_novo_menor_historico_gera_motivo_proprio(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        notificar_queda_preco=True,
    )

    matches = matching.processar_evento(
        evento(
            tipo="novo_menor_preco_historico",
            anterior=None,
        )
    )

    assert len(matches) == 1
    assert matches[0].motivos == ("new_historical_low",)


def test_evento_pode_acumular_motivos(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
        notificar_queda_preco=True,
    )

    matches = matching.processar_evento(evento(atual="900.00", anterior="1000.00"))

    assert matches[0].motivos == (
        "target_price_reached",
        "price_drop_detected",
    )


def test_notificacoes_desabilitadas_bloqueiam(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.atualizar_preferencias(
        conta_id=conta.id,
        notificacoes_preco_habilitadas=False,
        marketplaces_preferidos=[],
    )
    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
    )

    assert matching.processar_evento(evento()) == []


def test_marketplace_preferido_filtra(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.atualizar_preferencias(
        conta_id=conta.id,
        notificacoes_preco_habilitadas=True,
        marketplaces_preferidos=["shopee"],
    )
    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
    )

    assert matching.processar_evento(evento(marketplace="mercado_livre")) == []

    assert len(matching.processar_evento(evento(evento_id="evt_2", marketplace="shopee"))) == 1


def test_marketplace_ausente_com_preferencia_falha_fechada(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.atualizar_preferencias(
        conta_id=conta.id,
        notificacoes_preco_habilitadas=True,
        marketplaces_preferidos=["shopee"],
    )
    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
    )

    assert matching.processar_evento(evento(marketplace=None)) == []


def test_canonical_key_isola_watchlists(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="cpu_teste",
        preco_alvo="950.00",
    )

    assert matching.processar_evento(evento()) == []


def test_usuarios_independentes_recebem_matches_independentes(contexto):
    (
        _,
        identity_service,
        pservice,
        _,
        _,
        matching,
        conta_a,
    ) = contexto

    conta_b = identity_service.criar_conta(
        email="outro@example.com",
        senha="outra-senha-forte-456",
    )

    for conta in (conta_a, conta_b):
        pservice.adicionar_ou_atualizar_watchlist(
            conta_id=conta.id,
            canonical_key="gpu_teste",
            preco_alvo="950.00",
            notificar_queda_preco=False,
        )

    matches = matching.processar_evento(evento())

    assert len(matches) == 2
    assert {m.conta_id for m in matches} == {
        conta_a.id,
        conta_b.id,
    }


def test_reprocessamento_e_idempotente(contexto):
    _, _, pservice, _, match_repo, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
        notificar_queda_preco=False,
    )

    primeiro = matching.processar_evento(evento())
    segundo = matching.processar_evento(evento())

    assert len(primeiro) == 1
    assert len(segundo) == 1
    assert primeiro[0].id == segundo[0].id
    assert len(match_repo.listar_por_conta(conta.id)) == 1


def test_persistencia_preco_em_centavos(contexto):
    banco, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
        notificar_queda_preco=False,
    )
    matching.processar_evento(evento(atual="899.91"))

    with sqlite3.connect(banco) as conexao:
        valor = conexao.execute("""
            SELECT preco_atual_centavos
            FROM personalized_alert_matches
            """).fetchone()[0]

    assert valor == 89991


def test_evento_desconhecido_nao_gera_match(contexto):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
    )

    assert matching.processar_evento(evento(tipo="evento_desconhecido")) == []


@pytest.mark.parametrize("valor", ["0", "-1", "NaN"])
def test_preco_evento_invalido_falha(contexto, valor):
    _, _, pservice, _, _, matching, conta = contexto

    pservice.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="950.00",
    )

    with pytest.raises(ValueError, match="Preco de evento"):
        matching.processar_evento(evento(atual=valor))


def test_bloco_nao_adiciona_rotas_http():
    fonte = API_SERVER.read_text(encoding="utf-8")
    proibidas = (
        "/api/v1/alertas-personalizados",
        "/api/v1/watchlist-alerts",
        "/api/v1/notifications",
    )
    assert all(rota not in fonte for rota in proibidas)


def test_documentacao_declara_sem_delivery():
    texto = " ".join(DOC.read_text(encoding="utf-8").split())

    assert "nenhuma nova rota HTTP é criada" in texto
    assert "não existe entrega de notificação" in texto
    assert "envia push" in texto
    assert "publica no Telegram" in texto
    assert "não uma entrega" in texto
