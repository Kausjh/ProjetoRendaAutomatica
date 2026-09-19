from __future__ import annotations

import json
import sqlite3
from datetime import (
    UTC,
    datetime,
    timedelta,
)
from pathlib import Path

import pytest

from repositories.gamification_repository import (
    GamificationRepository,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.gamification_rules import (
    ConjuntoRegrasGamificacao,
    RegraGamificacao,
)
from services.gamification_service import (
    ConflitoEventoGamificacao,
    ContaGamificacaoInvalida,
    EventoGamificacaoDesconhecido,
    GamificationService,
    LimiteGamificacaoExcedido,
)
from services.user_identity_service import (
    UserIdentityService,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "gamification_reputation_core_v1.json"

DOC = ROOT / "docs" / "48-gamification-reputation-core-v1.md"


def criar_contexto(
    tmp_path: Path,
):
    db = tmp_path / "user_identity.sqlite3"

    identity_repository = UserIdentityRepository(db)

    identity_service = UserIdentityService(identity_repository)

    conta = identity_service.criar_conta(
        email=("gamification@example.com"),
        senha=("senha-forte-" "gamification-123"),
    )

    repository = GamificationRepository(db)

    ruleset = ConjuntoRegrasGamificacao(
        versao="test-v1",
        regras=(
            RegraGamificacao(
                tipo_evento=("acao_util"),
                xp_delta=120,
                reputacao_delta=3,
            ),
            RegraGamificacao(
                tipo_evento=("acao_limitada"),
                xp_delta=5,
                reputacao_delta=0,
                limite_por_janela=2,
                janela_segundos=3600,
            ),
        ),
        niveis_xp=(
            0,
            100,
            250,
        ),
    )

    service = GamificationService(
        repository=repository,
        identity_repository=(identity_repository),
        ruleset=ruleset,
    )

    return (
        db,
        conta,
        repository,
        service,
    )


def test_schema_core_fica_no_mesmo_sqlite_da_identidade(
    tmp_path: Path,
):
    db, _, _, _ = criar_contexto(tmp_path)

    with sqlite3.connect(db) as conexao:
        tabelas = {linha[0] for linha in (conexao.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type='table'
                    """))}

    assert "contas_usuario" in tabelas
    assert "gamification_events" in tabelas
    assert "gamification_profiles" in tabelas


def test_perfil_inicial_e_nivel_um(
    tmp_path: Path,
):
    _, conta, _, service = criar_contexto(tmp_path)

    perfil = service.obter_perfil(conta.id)

    assert perfil.conta_id == conta.id
    assert perfil.xp_total == 0
    assert perfil.reputacao_total == 0
    assert perfil.eventos_total == 0
    assert perfil.nivel == 1


def test_evento_aplica_regra_versionada_e_atualiza_perfil(
    tmp_path: Path,
):
    _, conta, _, service = criar_contexto(tmp_path)

    resultado = service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia=("acao:1"),
        tipo_evento="acao_util",
        origem="teste",
        origem_id="origem-1",
        metadados={"chave": "valor"},
    )

    assert resultado.criado is True
    assert resultado.evento.xp_delta == 120
    assert resultado.evento.reputacao_delta == 3
    assert resultado.evento.regra_versao == "test-v1"
    assert resultado.evento.metadados == {"chave": "valor"}
    assert resultado.perfil.xp_total == 120
    assert resultado.perfil.reputacao_total == 3
    assert resultado.perfil.eventos_total == 1
    assert resultado.perfil.nivel == 2


def test_idempotencia_nao_duplica_xp_nem_reputacao(
    tmp_path: Path,
):
    _, conta, _, service = criar_contexto(tmp_path)

    primeiro = service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia=("acao:1"),
        tipo_evento="acao_util",
        origem="teste",
    )

    segundo = service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia=("acao:1"),
        tipo_evento="acao_util",
        origem="teste",
    )

    assert primeiro.criado is True
    assert segundo.criado is False
    assert segundo.evento.id == primeiro.evento.id
    assert segundo.perfil.xp_total == 120
    assert segundo.perfil.reputacao_total == 3
    assert segundo.perfil.eventos_total == 1


def test_eventos_distintos_acumulam_e_elevam_nivel(
    tmp_path: Path,
):
    _, conta, _, service = criar_contexto(tmp_path)

    service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia="acao:1",
        tipo_evento="acao_util",
        origem="teste",
    )

    segundo = service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia=("acao:2"),
        tipo_evento="acao_util",
        origem="teste",
    )

    assert segundo.perfil.xp_total == 240
    assert segundo.perfil.nivel == 2

    terceiro = service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia=("acao:3"),
        tipo_evento="acao_util",
        origem="teste",
    )

    assert terceiro.perfil.xp_total == 360
    assert terceiro.perfil.nivel == 3


def test_evento_sem_regra_versionada_e_bloqueado(
    tmp_path: Path,
):
    _, conta, _, service = criar_contexto(tmp_path)

    with pytest.raises(EventoGamificacaoDesconhecido):
        service.registrar_evento(
            conta_id=conta.id,
            chave_idempotencia=("desconhecido:1"),
            tipo_evento=("evento_desconhecido"),
            origem="teste",
        )


def test_limite_anti_farming_bloqueia_terceiro_evento(
    tmp_path: Path,
):
    _, conta, _, service = criar_contexto(tmp_path)

    inicio = datetime(
        2026,
        9,
        19,
        12,
        0,
        tzinfo=UTC,
    )

    for indice in range(2):
        service.registrar_evento(
            conta_id=conta.id,
            chave_idempotencia=(f"limitada:{indice}"),
            tipo_evento=("acao_limitada"),
            origem="teste",
            ocorrido_em=(inicio + timedelta(seconds=indice)),
        )

    with pytest.raises(LimiteGamificacaoExcedido):
        service.registrar_evento(
            conta_id=conta.id,
            chave_idempotencia=("limitada:2"),
            tipo_evento=("acao_limitada"),
            origem="teste",
            ocorrido_em=(inicio + timedelta(seconds=2)),
        )


def test_retry_idempotente_nao_e_bloqueado_pelo_limite(
    tmp_path: Path,
):
    _, conta, _, service = criar_contexto(tmp_path)

    inicio = datetime(
        2026,
        9,
        19,
        12,
        0,
        tzinfo=UTC,
    )

    primeiro = service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia=("limitada:1"),
        tipo_evento=("acao_limitada"),
        origem="teste",
        ocorrido_em=inicio,
    )

    service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia=("limitada:2"),
        tipo_evento=("acao_limitada"),
        origem="teste",
        ocorrido_em=(inicio + timedelta(seconds=1)),
    )

    retry = service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia=("limitada:1"),
        tipo_evento=("acao_limitada"),
        origem="teste",
        ocorrido_em=(inicio + timedelta(seconds=2)),
    )

    assert retry.criado is False
    assert retry.evento.id == primeiro.evento.id


def test_conta_inexistente_nao_pode_receber_evento(
    tmp_path: Path,
):
    _, _, _, service = criar_contexto(tmp_path)

    with pytest.raises(ContaGamificacaoInvalida):
        service.registrar_evento(
            conta_id="usr_inexistente",
            chave_idempotencia=("acao:1"),
            tipo_evento="acao_util",
            origem="teste",
        )


def test_historico_e_auditavel_e_preserva_origem(
    tmp_path: Path,
):
    _, conta, _, service = criar_contexto(tmp_path)

    service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia=("acao:1"),
        tipo_evento="acao_util",
        origem=("community_discovery"),
        origem_id="discovery-123",
        metadados={"status": "approved"},
    )

    historico = service.listar_eventos(conta.id)

    assert len(historico) == 1
    assert historico[0].origem == "community_discovery"
    assert historico[0].origem_id == "discovery-123"
    assert historico[0].metadados == {"status": "approved"}
    assert historico[0].regra_versao == "test-v1"


def test_ruleset_exige_thresholds_estritamente_crescentes():
    with pytest.raises(ValueError):
        ConjuntoRegrasGamificacao(
            versao="v1",
            regras=(),
            niveis_xp=(
                0,
                100,
                100,
            ),
        )


def test_regra_exige_limite_e_janela_em_conjunto():
    with pytest.raises(ValueError):
        RegraGamificacao(
            tipo_evento="teste",
            xp_delta=1,
            limite_por_janela=2,
        )


def test_contrato_6a_e_fail_closed_sem_regras_de_producao():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "core-ledger"
    assert data["database"] == "database/user_identity.sqlite3"
    assert data["rules"]["production_rules_defined"] is False
    assert data["authority"]["client_can_set_xp"] is False
    assert data["authority"]["client_can_set_reputation"] is False
    assert data["anti_abuse"]["idempotency_per_account"] is True
    assert data["anti_abuse"]["atomic_window_limit_per_rule"] is True
    assert data["boundaries"]["community_discovery_wiring"] is False
    assert data["boundaries"]["offer_scoring_influence"] is False


def test_documentacao_preserva_fronteira_com_etapas_7_e_8():
    source = DOC.read_text(encoding="utf-8")

    assert "Etapa 6A" in source
    assert "Etapa 7" in source
    assert "Etapa 8" in source

    assert "nao concede XP nem reputacao " "automaticamente" in source

    assert "nao altera preco, curadoria " "ou qualidade objetiva" in source


def test_colisao_de_idempotencia_com_semantica_diferente_falha_fechado(
    tmp_path: Path,
):
    _, conta, _, service = criar_contexto(tmp_path)

    service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia="colisao:1",
        tipo_evento="acao_util",
        origem="teste",
        metadados={"origem": "primeira"},
    )

    with pytest.raises(ConflitoEventoGamificacao):
        service.registrar_evento(
            conta_id=conta.id,
            chave_idempotencia=("colisao:1"),
            tipo_evento=("acao_limitada"),
            origem="teste",
            metadados={"origem": "segunda"},
        )

    perfil = service.obter_perfil(conta.id)

    assert perfil.xp_total == 120
    assert perfil.reputacao_total == 3
    assert perfil.eventos_total == 1


def test_timestamp_futuro_nao_contorna_limite_anti_farming(
    tmp_path: Path,
):
    _, conta, _, service = criar_contexto(tmp_path)

    agora = datetime.now(UTC)

    service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia="janela:1",
        tipo_evento="acao_limitada",
        origem="teste",
        ocorrido_em=agora,
    )

    service.registrar_evento(
        conta_id=conta.id,
        chave_idempotencia="janela:2",
        tipo_evento="acao_limitada",
        origem="teste",
        ocorrido_em=(agora + timedelta(seconds=1)),
    )

    with pytest.raises(LimiteGamificacaoExcedido):
        service.registrar_evento(
            conta_id=conta.id,
            chave_idempotencia=("janela:3"),
            tipo_evento=("acao_limitada"),
            origem="teste",
            ocorrido_em=(agora + timedelta(days=2)),
        )


def test_contrato_6a_endurece_idempotencia_e_janela():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    anti_abuse = data["anti_abuse"]

    assert anti_abuse["idempotency_collision_fails_closed"] is True

    assert anti_abuse["window_uses_server_persistence_time"] is True
