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
from services.gamification_event_wiring import (
    GamificationEventWiring,
)
from services.gamification_production_rules import (
    criar_ruleset_producao_v1,
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

CONTRACT = ROOT / "contracts" / "gamification_reputation_event_wiring_v1.json"


def contexto(tmp_path: Path):
    db = tmp_path / "user_identity.sqlite3"

    identity_repository = UserIdentityRepository(db)

    identity_service = UserIdentityService(repository=(identity_repository))

    personalization_repository = UserPersonalizationRepository(db)

    personalization_service = UserPersonalizationService(
        repository=(personalization_repository),
        identity_repository=(identity_repository),
    )

    gamification_repository = GamificationRepository(db)

    gamification_service = GamificationService(
        repository=(gamification_repository),
        identity_repository=(identity_repository),
        ruleset=(criar_ruleset_producao_v1()),
    )

    wiring = GamificationEventWiring(gamification_service)

    identity_service.configurar_gamificacao(wiring)

    personalization_service.configurar_gamificacao(wiring)

    return {
        "db": db,
        "identity_repository": (identity_repository),
        "identity": identity_service,
        "personalization": (personalization_service),
        "gamification": (gamification_service),
        "wiring": wiring,
    }


def criar_conta(ctx):
    return ctx["identity"].criar_conta(
        email="usuario@example.com",
        senha="senha-forte-123456",
    )


def test_criar_conta_registra_40_xp(
    tmp_path: Path,
):
    ctx = contexto(tmp_path)

    conta = criar_conta(ctx)

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 40
    assert perfil.reputacao_total == 0
    assert perfil.eventos_total == 1


def test_primeiro_dispositivo_pontua_uma_vez(
    tmp_path: Path,
):
    ctx = contexto(tmp_path)
    conta = criar_conta(ctx)

    ctx["identity"].registrar_dispositivo(
        conta_id=conta.id,
        instalacao_id="instalacao-0001",
        plataforma="android",
        push_token="token-device-0001",
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 60

    ctx["identity"].registrar_dispositivo(
        conta_id=conta.id,
        instalacao_id="instalacao-0002",
        plataforma="android",
        push_token="token-device-0002",
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 60


def test_rotacao_de_token_nao_pontua_novamente(
    tmp_path: Path,
):
    ctx = contexto(tmp_path)
    conta = criar_conta(ctx)

    ctx["identity"].registrar_dispositivo(
        conta_id=conta.id,
        instalacao_id="instalacao-0001",
        plataforma="android",
        push_token="token-device-0001",
    )

    ctx["identity"].registrar_dispositivo(
        conta_id=conta.id,
        instalacao_id="instalacao-0001",
        plataforma="android",
        push_token="token-device-0001-rotated",
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 60


def test_preferencias_pontuam_so_na_primeira_persistencia(
    tmp_path: Path,
):
    ctx = contexto(tmp_path)
    conta = criar_conta(ctx)

    ctx["personalization"].atualizar_preferencias(
        conta_id=conta.id,
        notificacoes_preco_habilitadas=True,
        marketplaces_preferidos=["mercado_livre"],
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 60

    ctx["personalization"].atualizar_preferencias(
        conta_id=conta.id,
        notificacoes_preco_habilitadas=False,
        marketplaces_preferidos=["kabum"],
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 60


def test_novo_item_watchlist_sem_alvo_concede_20_xp(
    tmp_path: Path,
):
    ctx = contexto(tmp_path)
    conta = criar_conta(ctx)

    ctx["personalization"].adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto:gpu:001",
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 60


def test_novo_item_com_preco_alvo_concede_30_xp(
    tmp_path: Path,
):
    ctx = contexto(tmp_path)
    conta = criar_conta(ctx)

    ctx["personalization"].adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto:gpu:001",
        preco_alvo="999.90",
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 70
    assert perfil.eventos_total == 3


def test_primeiro_preco_alvo_em_item_existente_concede_10_xp(
    tmp_path: Path,
):
    ctx = contexto(tmp_path)
    conta = criar_conta(ctx)

    ctx["personalization"].adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto:gpu:001",
    )

    ctx["personalization"].adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto:gpu:001",
        preco_alvo="900.00",
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 70


def test_alterar_preco_alvo_nao_pontua_novamente(
    tmp_path: Path,
):
    ctx = contexto(tmp_path)
    conta = criar_conta(ctx)

    ctx["personalization"].adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto:gpu:001",
        preco_alvo="900.00",
    )

    ctx["personalization"].adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto:gpu:001",
        preco_alvo="850.00",
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 70


def test_remover_e_readicionar_nao_duplica_xp(
    tmp_path: Path,
):
    ctx = contexto(tmp_path)
    conta = criar_conta(ctx)

    ctx["personalization"].adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto:gpu:001",
        preco_alvo="900.00",
    )

    ctx["personalization"].remover_watchlist(
        conta_id=conta.id,
        canonical_key="produto:gpu:001",
    )

    ctx["personalization"].adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto:gpu:001",
        preco_alvo="900.00",
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 70
    assert perfil.eventos_total == 3


def test_setup_basico_com_primeiro_item_chega_a_100_xp(
    tmp_path: Path,
):
    ctx = contexto(tmp_path)
    conta = criar_conta(ctx)

    ctx["identity"].registrar_dispositivo(
        conta_id=conta.id,
        instalacao_id="instalacao-0001",
        plataforma="android",
        push_token="token-device-0001",
    )

    ctx["personalization"].atualizar_preferencias(
        conta_id=conta.id,
        notificacoes_preco_habilitadas=True,
        marketplaces_preferidos=[],
    )

    ctx["personalization"].adicionar_ou_atualizar_watchlist(
        conta_id=conta.id,
        canonical_key="produto:gpu:001",
    )

    perfil = ctx["gamification"].obter_perfil(conta.id)

    assert perfil.xp_total == 100
    assert perfil.nivel == 2
    assert perfil.reputacao_total == 0


def test_wiring_e_fail_open_para_operacao_principal(
    tmp_path: Path,
):
    db = tmp_path / "identity.sqlite3"

    repository = UserIdentityRepository(db)

    service = UserIdentityService(repository=repository)

    class GamificationQuebrada:
        def registrar_evento(
            self,
            **kwargs,
        ):
            raise RuntimeError("falha simulada")

    wiring = GamificationEventWiring(GamificationQuebrada())

    service.configurar_gamificacao(wiring)

    conta = service.criar_conta(
        email="failopen@example.com",
        senha="senha-forte-123456",
    )

    assert conta.id.startswith("usr_")

    assert repository.obter_conta(conta.id) is not None


def test_sem_configurar_wiring_comportamento_antigo_permanece(
    tmp_path: Path,
):
    db = tmp_path / "identity.sqlite3"

    repository = UserIdentityRepository(db)

    service = UserIdentityService(repository=repository)

    conta = service.criar_conta(
        email="legacy@example.com",
        senha="senha-forte-123456",
    )

    assert conta.id.startswith("usr_")


def test_contract_6c1_mantem_runtime_desligado():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "domain-event-wiring"

    assert data["wiring"]["identity_service"] is True

    assert data["wiring"]["personalization_service"] is True

    assert data["wiring"]["runtime_composition"] is False

    assert data["wiring"]["reconciliation"] is False

    assert data["failure_policy"]["event_wiring_fail_open"] is True

    assert data["boundaries"]["public_api"] is False

    assert data["boundaries"]["community_reputation"] is False
