from __future__ import annotations

from pathlib import Path

from repositories.gamification_repository import (
    GamificationRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.gamification_production_rules import (
    VERSAO_RULESET_PRODUCAO_V1,
    criar_ruleset_producao_v1,
)
from services.gamification_read_service import (
    GamificationReadService,
)
from services.gamification_service import (
    GamificationService,
)
from services.user_identity_service import (
    UserIdentityService,
)


def criar_contexto(
    tmp_path: Path,
):
    db = tmp_path / "identity.sqlite3"

    identity_repository = UserIdentityRepository(db)

    identity_service = UserIdentityService(identity_repository)

    conta = identity_service.criar_conta(
        email="gamification@example.com",
        senha="uma-senha-forte-123",
    )

    service = GamificationService(
        repository=GamificationRepository(db),
        identity_repository=(identity_repository),
        ruleset=(criar_ruleset_producao_v1()),
    )

    eventos = [
        (
            "v1:onboarding_conta_criada",
            "onboarding_conta_criada",
            conta.id,
        ),
        (
            "v1:onboarding_dispositivo_vinculado",
            "onboarding_dispositivo_vinculado",
            conta.id,
        ),
        (
            "v1:onboarding_preferencias_definidas",
            "onboarding_preferencias_definidas",
            conta.id,
        ),
        (
            "v1:watchlist_produto_adicionado:a",
            "watchlist_produto_adicionado",
            "a",
        ),
        (
            "v1:watchlist_preco_alvo_definido:a",
            "watchlist_preco_alvo_definido",
            "a",
        ),
        (
            "v1:watchlist_produto_adicionado:b",
            "watchlist_produto_adicionado",
            "b",
        ),
        (
            "v1:watchlist_preco_alvo_definido:b",
            "watchlist_preco_alvo_definido",
            "b",
        ),
    ]

    for (
        chave,
        tipo,
        origem_id,
    ) in eventos:
        service.registrar_evento(
            conta_id=conta.id,
            chave_idempotencia=chave,
            tipo_evento=tipo,
            origem="test_read_v1",
            origem_id=origem_id,
        )

    return (
        conta,
        service,
        GamificationReadService(service),
    )


def test_read_service_agrega_perfil_progresso_e_conquistas(
    tmp_path: Path,
):
    (
        conta,
        service,
        read_service,
    ) = criar_contexto(tmp_path)

    antes = service.obter_perfil(conta.id)

    leitura = read_service.obter(conta.id)

    depois = service.obter_perfil(conta.id)

    assert leitura.perfil.xp_total == 140
    assert leitura.perfil.nivel == 2
    assert leitura.perfil.reputacao_total == 0
    assert leitura.perfil.eventos_total == 7

    progresso = leitura.progresso_nivel

    assert progresso.nivel_atual == 2
    assert progresso.xp_total == 140
    assert progresso.xp_inicio_nivel == 100
    assert progresso.xp_proximo_nivel == 250
    assert progresso.xp_no_nivel == 40
    assert progresso.xp_necessario_no_nivel == 150
    assert progresso.xp_faltante == 110
    assert progresso.percentual == 26.67
    assert progresso.nivel_maximo is False

    conquistas = {item.codigo: item for item in leitura.conquistas}

    assert set(conquistas) == {
        "radar_ligado",
        "lista_5",
        "lista_10",
        "primeiro_alvo",
        "setup_completo",
        "nivel_5",
    }

    assert conquistas["radar_ligado"].desbloqueada is True

    assert conquistas["lista_5"].progresso_atual == 2

    assert conquistas["lista_5"].progresso_alvo == 5

    assert conquistas["lista_10"].progresso_atual == 2

    assert conquistas["primeiro_alvo"].desbloqueada is True

    assert conquistas["setup_completo"].desbloqueada is True

    assert conquistas["nivel_5"].progresso_atual == 2

    assert leitura.badges_desbloqueadas == (
        "radar-ligado",
        "preco-na-mira",
        "setup-completo",
    )

    assert leitura.ruleset_version == VERSAO_RULESET_PRODUCAO_V1

    assert depois.xp_total == antes.xp_total
    assert depois.reputacao_total == antes.reputacao_total
    assert depois.eventos_total == antes.eventos_total


def test_read_service_nao_cria_eventos(
    tmp_path: Path,
):
    (
        conta,
        service,
        read_service,
    ) = criar_contexto(tmp_path)

    assert service.obter_perfil(conta.id).eventos_total == 7

    for _ in range(3):
        leitura = read_service.obter(conta.id)

        assert leitura.perfil.eventos_total == 7

    assert service.obter_perfil(conta.id).eventos_total == 7
