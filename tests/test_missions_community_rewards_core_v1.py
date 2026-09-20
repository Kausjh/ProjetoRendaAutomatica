from __future__ import annotations

import json
from pathlib import Path

import pytest

from repositories.mission_repository import (
    MissionRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.mission_rules import (
    ConjuntoRegrasMissoes,
    DefinicaoMissao,
)
from services.mission_service import (
    ConflitoEventoMissao,
    ConflitoRecompensaMissao,
    ContaMissaoInvalida,
    EventoMissaoInvalido,
    MissaoDesconhecida,
    MissionService,
)
from services.user_identity_service import (
    UserIdentityService,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "missions_community_rewards_core_v1.json"


def contexto(
    tmp_path: Path,
):
    banco = tmp_path / "user_identity.sqlite3"

    identity_repository = UserIdentityRepository(banco)

    identity = UserIdentityService(identity_repository)

    conta = identity.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )

    ruleset = ConjuntoRegrasMissoes(
        versao="missions-test-v1",
        missoes=(
            DefinicaoMissao(
                codigo="primeira_aprovada",
                titulo="Primeira aprovada",
                descricao=("Tenha uma contribuicao " "aprovada."),
                tipo_evento=("community_discovery_approved"),
                alvo=1,
                recompensa_xp=20,
            ),
            DefinicaoMissao(
                codigo="tres_aprovadas",
                titulo="Tres aprovadas",
                descricao=("Tenha tres contribuicoes " "aprovadas."),
                tipo_evento=("community_discovery_approved"),
                alvo=3,
                recompensa_xp=50,
            ),
        ),
    )

    repository = MissionRepository(banco)

    service = MissionService(
        repository=repository,
        identity_repository=(identity_repository),
        ruleset=ruleset,
    )

    return (
        banco,
        identity,
        identity_repository,
        conta,
        repository,
        service,
        ruleset,
    )


def registrar(
    service: MissionService,
    *,
    conta_id: str,
    missao_codigo: str,
    numero: int,
    metadados: dict[str, object] | None = None,
):
    return service.registrar_evento(
        conta_id=conta_id,
        missao_codigo=missao_codigo,
        tipo_evento=("community_discovery_approved"),
        origem="community_discovery_v1",
        origem_id=f"discovery_{numero}",
        chave_idempotencia=("v1:community-approved:" f"discovery_{numero}"),
        metadados=metadados,
        ocorrido_em=(f"2026-09-20T10:0{numero}:00+00:00"),
    )


def test_progresso_e_conclusao_server_side(
    tmp_path: Path,
):
    (
        _,
        _,
        _,
        conta,
        repository,
        service,
        _,
    ) = contexto(tmp_path)

    primeiro = registrar(
        service,
        conta_id=conta.id,
        missao_codigo="tres_aprovadas",
        numero=1,
    )

    assert primeiro.status == "created"
    assert primeiro.progresso.progresso_total == 1
    assert primeiro.progresso.concluida is False
    assert primeiro.recompensa is None

    segundo = registrar(
        service,
        conta_id=conta.id,
        missao_codigo="tres_aprovadas",
        numero=2,
    )

    assert segundo.progresso.progresso_total == 2
    assert segundo.progresso.concluida is False

    terceiro = registrar(
        service,
        conta_id=conta.id,
        missao_codigo="tres_aprovadas",
        numero=3,
    )

    assert terceiro.status == "created"
    assert terceiro.concluida_agora is True
    assert terceiro.recompensa_criada is True
    assert terceiro.progresso.progresso_total == 3
    assert terceiro.progresso.concluida is True

    assert terceiro.recompensa is not None
    assert terceiro.recompensa.status == "pending"
    assert terceiro.recompensa.tipo_recompensa == "xp"
    assert terceiro.recompensa.quantidade == 50

    assert (
        len(
            repository.listar_eventos(
                conta_id=conta.id,
                missao_codigo="tres_aprovadas",
            )
        )
        == 3
    )

    pendentes = service.listar_recompensas_pendentes()

    assert len(pendentes) == 1
    assert pendentes[0].quantidade == 50


def test_replay_do_mesmo_evento_e_idempotente(
    tmp_path: Path,
):
    (
        _,
        _,
        _,
        conta,
        repository,
        service,
        _,
    ) = contexto(tmp_path)

    primeiro = registrar(
        service,
        conta_id=conta.id,
        missao_codigo="tres_aprovadas",
        numero=1,
        metadados={
            "marketplace": "kabum",
        },
    )

    segundo = registrar(
        service,
        conta_id=conta.id,
        missao_codigo="tres_aprovadas",
        numero=1,
        metadados={
            "marketplace": "kabum",
        },
    )

    assert primeiro.status == "created"
    assert segundo.status == "idempotent"
    assert segundo.progresso.progresso_total == 1

    assert (
        len(
            repository.listar_eventos(
                conta_id=conta.id,
                missao_codigo="tres_aprovadas",
            )
        )
        == 1
    )


def test_colisao_de_idempotencia_falha_fechado(
    tmp_path: Path,
):
    (
        _,
        _,
        _,
        conta,
        _,
        service,
        _,
    ) = contexto(tmp_path)

    registrar(
        service,
        conta_id=conta.id,
        missao_codigo="tres_aprovadas",
        numero=1,
        metadados={
            "marketplace": "kabum",
        },
    )

    with pytest.raises(ConflitoEventoMissao):
        service.registrar_evento(
            conta_id=conta.id,
            missao_codigo="tres_aprovadas",
            tipo_evento=("community_discovery_approved"),
            origem="community_discovery_v1",
            origem_id="discovery_alterada",
            chave_idempotencia=("v1:community-approved:" "discovery_1"),
            metadados={
                "marketplace": "shopee",
            },
        )


def test_novo_evento_apos_conclusao_nao_duplica(
    tmp_path: Path,
):
    (
        _,
        _,
        _,
        conta,
        repository,
        service,
        _,
    ) = contexto(tmp_path)

    primeiro = registrar(
        service,
        conta_id=conta.id,
        missao_codigo="primeira_aprovada",
        numero=1,
    )

    assert primeiro.concluida_agora is True
    assert primeiro.recompensa is not None

    segundo = registrar(
        service,
        conta_id=conta.id,
        missao_codigo="primeira_aprovada",
        numero=2,
    )

    assert segundo.status == "completed"
    assert segundo.evento is None
    assert segundo.recompensa_criada is False

    assert (
        len(
            repository.listar_eventos(
                conta_id=conta.id,
                missao_codigo="primeira_aprovada",
            )
        )
        == 1
    )

    assert len(service.listar_recompensas_pendentes()) == 1


def test_mesma_chave_e_isolada_por_conta(
    tmp_path: Path,
):
    (
        _,
        identity,
        _,
        conta_a,
        _,
        service,
        _,
    ) = contexto(tmp_path)

    conta_b = identity.criar_conta(
        email="outro@example.com",
        senha="uma-senha-forte-123",
    )

    a = registrar(
        service,
        conta_id=conta_a.id,
        missao_codigo="tres_aprovadas",
        numero=1,
    )

    b = registrar(
        service,
        conta_id=conta_b.id,
        missao_codigo="tres_aprovadas",
        numero=1,
    )

    assert a.status == "created"
    assert b.status == "created"
    assert a.evento is not None
    assert b.evento is not None
    assert a.evento.conta_id != b.evento.conta_id


def test_tipo_de_evento_incorreto_e_rejeitado(
    tmp_path: Path,
):
    (
        _,
        _,
        _,
        conta,
        _,
        service,
        _,
    ) = contexto(tmp_path)

    with pytest.raises(EventoMissaoInvalido):
        service.registrar_evento(
            conta_id=conta.id,
            missao_codigo="tres_aprovadas",
            tipo_evento="community_discovery_received",
            origem="community_discovery_v1",
            origem_id="discovery_1",
            chave_idempotencia="evento_1",
        )


def test_missao_desconhecida_e_rejeitada(
    tmp_path: Path,
):
    (
        _,
        _,
        _,
        conta,
        _,
        service,
        _,
    ) = contexto(tmp_path)

    with pytest.raises(MissaoDesconhecida):
        service.registrar_evento(
            conta_id=conta.id,
            missao_codigo="nao_existe",
            tipo_evento=("community_discovery_approved"),
            origem="community_discovery_v1",
            origem_id="discovery_1",
            chave_idempotencia="evento_1",
        )


def test_conta_inexistente_e_rejeitada(
    tmp_path: Path,
):
    (
        _,
        _,
        _,
        _,
        _,
        service,
        _,
    ) = contexto(tmp_path)

    with pytest.raises(ContaMissaoInvalida):
        service.registrar_evento(
            conta_id="usr_inexistente",
            missao_codigo="tres_aprovadas",
            tipo_evento=("community_discovery_approved"),
            origem="community_discovery_v1",
            origem_id="discovery_1",
            chave_idempotencia="evento_1",
        )


def test_liquidacao_da_recompensa_e_idempotente(
    tmp_path: Path,
):
    (
        _,
        _,
        _,
        conta,
        _,
        service,
        _,
    ) = contexto(tmp_path)

    resultado = registrar(
        service,
        conta_id=conta.id,
        missao_codigo="primeira_aprovada",
        numero=1,
    )

    assert resultado.recompensa is not None

    concedida, alterou = service.marcar_recompensa_concedida(
        recompensa_id=(resultado.recompensa.id),
        referencia_concessao=("gamification:event:abc"),
    )

    assert alterou is True
    assert concedida.status == "granted"
    assert concedida.referencia_concessao == "gamification:event:abc"

    repetida, alterou_novamente = service.marcar_recompensa_concedida(
        recompensa_id=(resultado.recompensa.id),
        referencia_concessao=("gamification:event:abc"),
    )

    assert alterou_novamente is False
    assert repetida.status == "granted"

    with pytest.raises(ConflitoRecompensaMissao):
        service.marcar_recompensa_concedida(
            recompensa_id=(resultado.recompensa.id),
            referencia_concessao=("gamification:event:outra"),
        )


def test_ruleset_rejeita_codigos_duplicados():
    missao = DefinicaoMissao(
        codigo="duplicada",
        titulo="Duplicada",
        descricao="Teste.",
        tipo_evento="evento",
        alvo=1,
        recompensa_xp=10,
    )

    with pytest.raises(ValueError):
        ConjuntoRegrasMissoes(
            versao="v1",
            missoes=(
                missao,
                missao,
            ),
        )


def test_ruleset_lista_multiplas_missoes_por_evento():
    ruleset = ConjuntoRegrasMissoes(
        versao="v1",
        missoes=(
            DefinicaoMissao(
                codigo="um",
                titulo="Um",
                descricao="",
                tipo_evento="approved",
                alvo=1,
                recompensa_xp=10,
            ),
            DefinicaoMissao(
                codigo="tres",
                titulo="Tres",
                descricao="",
                tipo_evento="approved",
                alvo=3,
                recompensa_xp=30,
            ),
        ),
    )

    encontradas = ruleset.listar_por_evento("approved")

    assert [item.codigo for item in encontradas] == [
        "um",
        "tres",
    ]


def test_contract_preserva_fronteiras_7a():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == ("7A-mission-engine-core")

    assert data["source_of_truth"]["progress"] == "server-side"

    assert data["source_of_truth"]["completion"] == "server-side"

    assert data["idempotency"]["semantic_collision_fails_closed"] is True

    assert data["idempotency"]["completion_creates_one_reward"] is True

    assert data["rewards"]["core_reward_type"] == "xp"

    assert data["rewards"]["settlement_to_gamification"] is False

    assert data["rewards"]["reputation_reward"] is False

    boundaries = data["boundaries"]

    assert boundaries["production_mission_catalog"] is False

    assert boundaries["community_discovery_wiring"] is False

    assert boundaries["runtime_wiring"] is False

    assert boundaries["public_api"] is False

    assert boundaries["public_app"] is False

    assert boundaries["stage8_community_reputation"] is False

    assert boundaries["stage8_contributor_trust"] is False

    assert boundaries["offer_scoring_change"] is False

    assert boundaries["price_intelligence_change"] is False

    assert data["next_step"] == ("7B-production-mission-catalog-" "and-reward-policy")
