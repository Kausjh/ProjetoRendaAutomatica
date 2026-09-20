from __future__ import annotations

import json
from pathlib import Path

from repositories.gamification_repository import (
    GamificationRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)
from services.gamification_production_rules import (
    criar_ruleset_producao_v1,
)
from services.gamification_runtime import (
    ativar_gamificacao_runtime,
)
from services.gamification_service import (
    GamificationService,
)
from services.user_identity_service import (
    UserIdentityService,
)
from services.user_personalization_service import (
    UserPersonalizationService,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "gamification_reputation_runtime_v1.json"


def preparar_historico(
    tmp_path: Path,
):
    db = tmp_path / "user_identity.sqlite3"

    identity_repository = UserIdentityRepository(db)

    identity_service = UserIdentityService(identity_repository)

    personalization_repository = UserPersonalizationRepository(db)

    personalization_service = UserPersonalizationService(
        personalization_repository,
        identity_repository,
    )

    conta = identity_service.criar_conta(
        email="historico@example.com",
        senha="senha-forte-123456",
    )

    identity_service.registrar_dispositivo(
        conta_id=conta.id,
        instalacao_id="instalacao-0001",
        plataforma="android",
        push_token="token-device-0001",
    )

    personalization_service.atualizar_preferencias(
        conta_id=conta.id,
        notificacoes_preco_habilitadas=True,
        marketplaces_preferidos=["mercado_livre"],
    )

    personalization_service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="ryzen_7_5700x",
        preco_alvo="999.90",
    )

    personalization_service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="rtx_3060_ti",
        preco_alvo="1999.90",
    )

    return (
        db,
        conta,
        identity_repository,
        identity_service,
        personalization_repository,
        personalization_service,
    )


def obter_perfil(
    *,
    db: Path,
    conta_id: str,
    identity_repository: UserIdentityRepository,
):
    service = GamificationService(
        repository=GamificationRepository(db),
        identity_repository=(identity_repository),
        ruleset=(criar_ruleset_producao_v1()),
    )

    return service.obter_perfil(conta_id)


def test_reconciliacao_historica_cria_140_xp(
    tmp_path: Path,
):
    (
        db,
        conta,
        identity_repository,
        identity_service,
        personalization_repository,
        personalization_service,
    ) = preparar_historico(tmp_path)

    resultado = ativar_gamificacao_runtime(
        caminho_banco=db,
        user_identity_repository=(identity_repository),
        user_identity_service=(identity_service),
        user_personalization_repository=(personalization_repository),
        user_personalization_service=(personalization_service),
    )

    assert resultado.ativo is True
    assert resultado.erro is None
    assert resultado.reconciliacao is not None

    assert resultado.reconciliacao.contas_processadas == 1

    assert resultado.reconciliacao.eventos_criados == 7

    assert resultado.reconciliacao.eventos_idempotentes == 0

    assert resultado.reconciliacao.falhas == ()

    perfil = obter_perfil(
        db=db,
        conta_id=conta.id,
        identity_repository=(identity_repository),
    )

    assert perfil.xp_total == 140
    assert perfil.nivel == 2
    assert perfil.eventos_total == 7
    assert perfil.reputacao_total == 0


def test_segunda_reconciliacao_e_idempotente(
    tmp_path: Path,
):
    (
        db,
        conta,
        identity_repository,
        identity_service,
        personalization_repository,
        personalization_service,
    ) = preparar_historico(tmp_path)

    primeiro = ativar_gamificacao_runtime(
        caminho_banco=db,
        user_identity_repository=(identity_repository),
        user_identity_service=(identity_service),
        user_personalization_repository=(personalization_repository),
        user_personalization_service=(personalization_service),
    )

    assert primeiro.ativo is True

    segundo = ativar_gamificacao_runtime(
        caminho_banco=db,
        user_identity_repository=(identity_repository),
        user_identity_service=(identity_service),
        user_personalization_repository=(personalization_repository),
        user_personalization_service=(personalization_service),
    )

    assert segundo.ativo is True
    assert segundo.reconciliacao is not None

    assert segundo.reconciliacao.eventos_criados == 0

    assert segundo.reconciliacao.eventos_idempotentes == 7

    perfil = obter_perfil(
        db=db,
        conta_id=conta.id,
        identity_repository=(identity_repository),
    )

    assert perfil.xp_total == 140
    assert perfil.eventos_total == 7


def test_wiring_fica_ativo_depois_da_reconciliacao(
    tmp_path: Path,
):
    (
        db,
        conta,
        identity_repository,
        identity_service,
        personalization_repository,
        personalization_service,
    ) = preparar_historico(tmp_path)

    resultado = ativar_gamificacao_runtime(
        caminho_banco=db,
        user_identity_repository=(identity_repository),
        user_identity_service=(identity_service),
        user_personalization_repository=(personalization_repository),
        user_personalization_service=(personalization_service),
    )

    assert resultado.ativo is True

    personalization_service.adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="ssd_nvme_1tb",
        preco_alvo="399.90",
    )

    perfil = obter_perfil(
        db=db,
        conta_id=conta.id,
        identity_repository=(identity_repository),
    )

    assert perfil.xp_total == 170
    assert perfil.eventos_total == 9
    assert perfil.reputacao_total == 0


def test_runtime_faz_reconciliacao_antes_da_api():
    source = (ROOT / "runtime.py").read_text(encoding="utf-8")

    composicao = source.index("gamification_runtime = " "ativar_gamificacao_runtime(")

    feed = source.index("personalized_feed_service = " "PersonalizedFeedService(")

    servidor = source.index("servidor_api = " "ServidorApiAplicacao(")

    assert composicao < feed
    assert composicao < servidor


def test_contract_6c2_preserva_fronteiras():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == ("runtime-composition-and-" "reconciliation")

    assert data["runtime"]["composition_defined"] is True

    assert data["runtime"]["reconciliation_before_wiring"] is True

    assert data["runtime"]["wiring_enabled_only_after_success"] is True

    assert data["runtime"]["gamification_failure_blocks_main_runtime"] is False

    assert data["database"]["production_database_mutated_by_this_patch"] is False

    assert data["boundaries"]["public_api"] is False

    assert data["boundaries"]["public_app"] is False

    assert data["boundaries"]["community_reputation"] is False
