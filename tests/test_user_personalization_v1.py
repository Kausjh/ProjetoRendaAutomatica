from __future__ import annotations

import json
import sqlite3
from decimal import Decimal
from pathlib import Path

import pytest

from repositories.user_identity_repository import UserIdentityRepository
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)
from services.user_identity_service import UserIdentityService
from services.user_personalization_service import UserPersonalizationService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "user_personalization_v1.json"
DOC = ROOT / "docs" / "14-personalizacao-watchlists.md"
API_SERVER = ROOT / "services" / "api_aplicacao" / "servidor.py"


@pytest.fixture
def contexto(tmp_path: Path):
    banco = tmp_path / "user_identity.sqlite3"
    identity_repo = UserIdentityRepository(banco)
    identity_service = UserIdentityService(identity_repo)
    personalization_repo = UserPersonalizationRepository(banco)
    service = UserPersonalizationService(
        personalization_repo,
        identity_repo,
    )

    conta = identity_service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )

    return banco, identity_service, service, conta


def test_contract_define_foundation_sem_rede():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["schema"] == "projeto-renda-automatica.user-personalization"
    assert data["personalization_version"] == 1
    assert data["stage"] == "foundation"
    assert data["network_exposure"] is False


def test_contract_preserva_fronteiras():
    boundaries = json.loads(CONTRACT.read_text(encoding="utf-8"))["boundaries"]
    assert boundaries["application_api_v1_remains_read_only"] is True
    assert boundaries["new_http_routes"] is False
    assert boundaries["personalized_alert_delivery"] is False
    assert boundaries["admin_api_is_not_personalization_api"] is True
    assert boundaries["infrastructure_bearer_is_not_user_identity"] is True


def test_preferencias_default_sao_seguras(contexto):
    _, _, service, conta = contexto
    prefs = service.obter_preferencias(conta.id)

    assert prefs.conta_id == conta.id
    assert prefs.notificacoes_preco_habilitadas is True
    assert prefs.marketplaces_preferidos == ()


def test_preferencias_normalizam_e_deduplicam_marketplaces(contexto):
    _, _, service, conta = contexto
    prefs = service.atualizar_preferencias(
        conta_id=conta.id,
        notificacoes_preco_habilitadas=False,
        marketplaces_preferidos=[
            " Mercado_Livre ",
            "shopee",
            "mercado_livre",
        ],
    )

    assert prefs.notificacoes_preco_habilitadas is False
    assert prefs.marketplaces_preferidos == (
        "mercado_livre",
        "shopee",
    )


def test_marketplace_invalido_falha(contexto):
    _, _, service, conta = contexto

    with pytest.raises(ValueError, match="Marketplace invalido"):
        service.atualizar_preferencias(
            conta_id=conta.id,
            notificacoes_preco_habilitadas=True,
            marketplaces_preferidos=["mercado livre"],
        )


def test_conta_inexistente_nao_pode_personalizar(contexto):
    _, _, service, _ = contexto

    with pytest.raises(ValueError, match="Conta inexistente ou inativa"):
        service.obter_preferencias("usr_inexistente")


def test_adiciona_watchlist_com_preco_alvo(contexto):
    _, _, service, conta = contexto
    item = service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="amd_ryzen_7_5700x",
        preco_alvo="999.90",
    )

    assert item.conta_id == conta.id
    assert item.canonical_key == "amd_ryzen_7_5700x"
    assert item.preco_alvo == Decimal("999.90")
    assert item.notificar_queda_preco is True
    assert item.id.startswith("wat_")


def test_preco_alvo_e_persistido_em_centavos(contexto):
    banco, _, service, conta = contexto
    service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="gpu_teste",
        preco_alvo="1234.56",
    )

    with sqlite3.connect(banco) as conexao:
        valor = conexao.execute(
            """
            SELECT preco_alvo_centavos
            FROM watchlist_usuario
            WHERE conta_id = ?
              AND canonical_key = ?
            """,
            (conta.id, "gpu_teste"),
        ).fetchone()[0]

    assert valor == 123456


@pytest.mark.parametrize("valor", [0, -1, "0.00", "-10.50", "NaN"])
def test_preco_alvo_invalido_falha(contexto, valor):
    _, _, service, conta = contexto

    with pytest.raises(ValueError, match="Preco alvo"):
        service.adicionar_ou_atualizar_watchlist(
            conta_id=conta.id,
            canonical_key="produto_teste",
            preco_alvo=valor,
        )


def test_watchlist_upsert_preserva_id_e_criacao(contexto):
    _, _, service, conta = contexto
    primeiro = service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto_x",
        preco_alvo="100.00",
    )
    segundo = service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto_x",
        preco_alvo="90.00",
        notificar_queda_preco=False,
    )

    assert segundo.id == primeiro.id
    assert segundo.criado_em == primeiro.criado_em
    assert segundo.preco_alvo == Decimal("90.00")
    assert segundo.notificar_queda_preco is False


def test_watchlist_isolada_por_usuario(contexto):
    _, identity_service, service, conta_a = contexto
    conta_b = identity_service.criar_conta(
        email="outro@example.com",
        senha="outra-senha-forte-456",
    )

    item_a = service.adicionar_ou_atualizar_watchlist(
        conta_id=conta_a.id,
        canonical_key="produto_compartilhado",
    )
    item_b = service.adicionar_ou_atualizar_watchlist(
        conta_id=conta_b.id,
        canonical_key="produto_compartilhado",
    )

    assert item_a.id != item_b.id
    assert len(service.listar_watchlist(conta_a.id)) == 1
    assert len(service.listar_watchlist(conta_b.id)) == 1


def test_remocao_afeta_somente_dono(contexto):
    _, identity_service, service, conta_a = contexto
    conta_b = identity_service.criar_conta(
        email="outro@example.com",
        senha="outra-senha-forte-456",
    )

    service.adicionar_ou_atualizar_watchlist(
        conta_id=conta_a.id,
        canonical_key="produto_x",
    )
    service.adicionar_ou_atualizar_watchlist(
        conta_id=conta_b.id,
        canonical_key="produto_x",
    )

    assert (
        service.remover_watchlist(
            conta_id=conta_a.id,
            canonical_key="produto_x",
        )
        is True
    )
    assert service.listar_watchlist(conta_a.id) == []
    assert len(service.listar_watchlist(conta_b.id)) == 1


def test_cascade_remove_personalizacao_quando_conta_e_removida(contexto):
    banco, _, service, conta = contexto
    service.obter_preferencias(conta.id)
    service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto_x",
    )

    with sqlite3.connect(banco) as conexao:
        conexao.execute("PRAGMA foreign_keys = ON")
        conexao.execute(
            "DELETE FROM contas_usuario WHERE id = ?",
            (conta.id,),
        )

    with sqlite3.connect(banco) as conexao:
        prefs = conexao.execute("SELECT COUNT(*) FROM preferencias_usuario").fetchone()[0]
        watch = conexao.execute("SELECT COUNT(*) FROM watchlist_usuario").fetchone()[0]

    assert prefs == 0
    assert watch == 0


def test_bloco_nao_adiciona_rotas_http():
    fonte = API_SERVER.read_text(encoding="utf-8")
    proibidas = (
        "/api/v1/preferencias",
        "/api/v1/watchlist",
        "/api/v1/watchlists",
    )
    assert all(rota not in fonte for rota in proibidas)


def test_documentacao_preserva_fronteiras():
    texto = " ".join(DOC.read_text(encoding="utf-8").split())

    assert "não cria rotas HTTP" in texto
    assert "não dispara Alert Engine" in texto
    assert "não envia push" in texto
    assert "Application API V1 continua read-only" in texto
