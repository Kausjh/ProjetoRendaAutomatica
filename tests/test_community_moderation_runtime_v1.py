from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import services.community_moderation_authority as authority_module
from services.community_moderation_authority import (
    CommunityModerationAuthorityV1,
)
from services.community_moderation_runtime import (
    RECONCILIATION_STARTUP_FLAG,
    RUNTIME_FLAG,
    ComponentesCommunityModerationRuntime,
    ativar_community_moderation_runtime,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_runtime_v1.json"


TOKEN = "token-admin-runtime-8e6"


def criar_banco_base(
    tmp_path: Path,
) -> Path:
    banco = tmp_path / "identity.sqlite3"

    with sqlite3.connect(banco) as conn:
        conn.execute("""
            CREATE TABLE contas_usuario (
                id TEXT PRIMARY KEY
            )
            """)

    return banco


def tabelas(
    banco: Path,
) -> set[str]:
    with sqlite3.connect(banco) as conn:
        return {str(row[0]) for row in conn.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """)}


def authority_teste():
    return CommunityModerationAuthorityV1(token_administrativo=TOKEN)


def preparar_contas(
    banco: Path,
):
    with sqlite3.connect(banco) as conn:

        for conta in (
            "contributor",
            "reporter",
        ):
            conn.execute(
                """
                INSERT INTO contas_usuario (
                    id
                )
                VALUES (?)
                """,
                (conta,),
            )


def registrar_discovery(
    componentes,
):
    discovery, criada = componentes.discovery_repository.registrar(
        descoberta_id="dsc-runtime",
        conta_id="contributor",
        url=("https://example.com/" "runtime"),
        url_normalizada=("https://example.com/" "runtime"),
        url_hash=("hash-runtime"),
        marketplace="example",
        agora=("2026-09-22T12:00:00+00:00"),
    )

    assert criada is True

    return discovery


def test_runtime_flag_desligada_nao_cria_schema(
    tmp_path: Path,
    monkeypatch,
):
    banco = criar_banco_base(tmp_path)

    monkeypatch.delenv(
        RUNTIME_FLAG,
        raising=False,
    )

    result = ativar_community_moderation_runtime(
        caminho_banco=banco,
        permitir_schema_activation=True,
        authority=authority_teste(),
    )

    assert result.ativo is False

    assert result.erro == "feature_flag_disabled"

    assert result.componentes is None

    names = tabelas(banco)

    assert "community_moderation_reports" not in names

    assert "community_discoveries" not in names

    assert "community_trust_evidence" not in names


def test_schema_permission_false_bloqueia_construtores(
    tmp_path: Path,
    monkeypatch,
):
    banco = criar_banco_base(tmp_path)

    monkeypatch.setenv(
        RUNTIME_FLAG,
        "1",
    )

    result = ativar_community_moderation_runtime(
        caminho_banco=banco,
        permitir_schema_activation=False,
        authority=authority_teste(),
    )

    assert result.ativo is False

    assert result.erro == "schema_activation_not_authorized"

    assert result.schema_activation_autorizada is False

    names = tabelas(banco)

    assert "community_moderation_reports" not in names

    assert "community_discoveries" not in names

    assert "community_trust_evidence" not in names


def test_authority_ausente_falha_antes_do_schema(
    tmp_path: Path,
    monkeypatch,
):
    banco = criar_banco_base(tmp_path)

    monkeypatch.setenv(
        RUNTIME_FLAG,
        "1",
    )

    monkeypatch.delenv(
        "RADAR_ADMIN_TOKEN",
        raising=False,
    )

    monkeypatch.setattr(
        authority_module,
        "load_dotenv",
        lambda: None,
    )

    result = ativar_community_moderation_runtime(
        caminho_banco=banco,
        permitir_schema_activation=True,
        authority=None,
    )

    assert result.ativo is False

    assert result.erro is not None

    assert "AutoridadeModeracaoIndisponivel" in result.erro

    names = tabelas(banco)

    assert "community_moderation_reports" not in names

    assert "community_discoveries" not in names

    assert "community_trust_evidence" not in names


def test_composicao_ativa_componentes_em_temp(
    tmp_path: Path,
    monkeypatch,
):
    banco = criar_banco_base(tmp_path)

    monkeypatch.setenv(
        RUNTIME_FLAG,
        "true",
    )

    result = ativar_community_moderation_runtime(
        caminho_banco=banco,
        permitir_schema_activation=True,
        authority=authority_teste(),
        executar_reconciliation=False,
    )

    assert result.ativo is True
    assert result.erro is None

    assert isinstance(
        result.componentes,
        ComponentesCommunityModerationRuntime,
    )

    assert result.reconciliation_executada is False

    names = tabelas(banco)

    assert "community_moderation_reports" in names

    assert "community_moderation_decisions" in names

    assert "community_discoveries" in names

    assert "community_trust_evidence" in names

    assert "community_trust_profiles" in names


def test_runtime_service_injeta_bridge(
    tmp_path: Path,
    monkeypatch,
):
    banco = criar_banco_base(tmp_path)

    preparar_contas(banco)

    monkeypatch.setenv(
        RUNTIME_FLAG,
        "1",
    )

    result = ativar_community_moderation_runtime(
        caminho_banco=banco,
        permitir_schema_activation=True,
        authority=authority_teste(),
        executar_reconciliation=False,
    )

    assert result.ativo is True

    componentes = result.componentes

    assert componentes is not None

    registrar_discovery(componentes)

    report = componentes.moderation_repository.registrar_denuncia(
        reporter_conta_id="reporter",
        target_type="community_discovery",
        target_id="dsc-runtime",
        motivo="spam",
        detalhes=None,
        agora=("2026-09-22T12:10:00+00:00"),
    ).denuncia

    decision = componentes.moderation_service.registrar_decisao_autorizada(
        authorization_header=(f"Bearer {TOKEN}"),
        denuncia_id=report.id,
        acao_idempotencia=("runtime-confirm"),
        resultado="confirmed_abuse",
        justificativa=None,
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    evidence = componentes.trust_repository.obter_evidencia_por_chave(
        conta_id="contributor",
        chave_idempotencia=(
            "v1:community-moderation:" "community-discovery:" "dsc-runtime:" "confirmed-abuse"
        ),
    )

    assert decision.criado is True
    assert evidence is not None

    assert evidence.classificacao == "negative"

    assert evidence.origem_id == decision.decisao.id


def test_reconciliation_nao_roda_por_default(
    tmp_path: Path,
    monkeypatch,
):
    banco = criar_banco_base(tmp_path)

    preparar_contas(banco)

    monkeypatch.setenv(
        RUNTIME_FLAG,
        "1",
    )

    monkeypatch.delenv(
        RECONCILIATION_STARTUP_FLAG,
        raising=False,
    )

    result = ativar_community_moderation_runtime(
        caminho_banco=banco,
        permitir_schema_activation=True,
        authority=authority_teste(),
    )

    assert result.ativo is True

    assert result.reconciliation_executada is False

    assert result.reconciliacao is None


def test_reconciliation_startup_repara_crash_gap(
    tmp_path: Path,
    monkeypatch,
):
    banco = criar_banco_base(tmp_path)

    preparar_contas(banco)

    monkeypatch.setenv(
        RUNTIME_FLAG,
        "1",
    )

    first = ativar_community_moderation_runtime(
        caminho_banco=banco,
        permitir_schema_activation=True,
        authority=authority_teste(),
        executar_reconciliation=False,
    )

    assert first.ativo is True

    componentes = first.componentes

    assert componentes is not None

    registrar_discovery(componentes)

    report = componentes.moderation_repository.registrar_denuncia(
        reporter_conta_id="reporter",
        target_type="community_discovery",
        target_id="dsc-runtime",
        motivo="spam",
        detalhes=None,
        agora=("2026-09-22T12:10:00+00:00"),
    ).denuncia

    persisted = componentes.moderation_repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia=("crash-gap"),
        moderator_actor_id=(CommunityModerationAuthorityV1.ACTOR_ID),
        resultado="confirmed_abuse",
        familia_abuso_confirmado=("spam_confirmado"),
        justificativa=None,
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    before = componentes.trust_repository.obter_evidencia_por_chave(
        conta_id="contributor",
        chave_idempotencia=(
            "v1:community-moderation:" "community-discovery:" "dsc-runtime:" "confirmed-abuse"
        ),
    )

    assert before is None

    second = ativar_community_moderation_runtime(
        caminho_banco=banco,
        permitir_schema_activation=True,
        authority=authority_teste(),
        executar_reconciliation=True,
    )

    assert second.ativo is True

    assert second.reconciliation_executada is True

    assert second.reconciliacao is not None

    assert second.reconciliacao.evidencias_criadas == 1

    assert second.reconciliacao.falhas == ()

    componentes_2 = second.componentes

    assert componentes_2 is not None

    after = componentes_2.trust_repository.obter_evidencia_por_chave(
        conta_id="contributor",
        chave_idempotencia=(
            "v1:community-moderation:" "community-discovery:" "dsc-runtime:" "confirmed-abuse"
        ),
    )

    assert after is not None

    assert after.origem_id == persisted.decisao.id


def test_reconciliation_com_falha_deixa_runtime_incompleto(
    tmp_path: Path,
    monkeypatch,
):
    banco = criar_banco_base(tmp_path)

    preparar_contas(banco)

    monkeypatch.setenv(
        RUNTIME_FLAG,
        "1",
    )

    first = ativar_community_moderation_runtime(
        caminho_banco=banco,
        permitir_schema_activation=True,
        authority=authority_teste(),
        executar_reconciliation=False,
    )

    assert first.ativo is True

    componentes = first.componentes

    assert componentes is not None

    registrar_discovery(componentes)

    report = componentes.moderation_repository.registrar_denuncia(
        reporter_conta_id="reporter",
        target_type="community_discovery",
        target_id="dsc-runtime",
        motivo="spam",
        detalhes=None,
        agora=("2026-09-22T12:10:00+00:00"),
    ).denuncia

    componentes.moderation_repository.registrar_decisao(
        denuncia_id=report.id,
        acao_idempotencia="bad-family",
        moderator_actor_id=(CommunityModerationAuthorityV1.ACTOR_ID),
        resultado="confirmed_abuse",
        familia_abuso_confirmado=("fraude_confirmada"),
        justificativa=None,
        ocorrido_em=("2026-09-22T12:20:00+00:00"),
    )

    second = ativar_community_moderation_runtime(
        caminho_banco=banco,
        permitir_schema_activation=True,
        authority=authority_teste(),
        executar_reconciliation=True,
    )

    assert second.ativo is False
    assert second.componentes is None

    assert second.reconciliation_executada is True

    assert second.reconciliacao is not None

    assert len(second.reconciliacao.falhas) == 1

    assert second.erro == "reconciliacao_incompleta:1"


def test_env_example_mantem_flags_desligadas():
    source = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert "COMMUNITY_MODERATION_RUNTIME_ATIVO=0" in source

    assert "COMMUNITY_MODERATION_RECONCILIATION_STARTUP_ATIVA=0" in source


def test_contract_8e6_boundaries():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E6-moderation-runtime-composition"

    assert data["status"] == "completed"

    activation = data["activation"]

    assert activation["runtime_default_enabled"] is False

    assert activation["schema_activation_requires_explicit_permission"] is True

    assert activation["flag_disabled_instantiates_repositories"] is False

    assert activation["schema_permission_missing_instantiates_repositories"] is False

    assert activation["authority_resolved_before_repository_instantiation"] is True

    assert activation["main_runtime_py_integration"] is False

    reconciliation = data["reconciliation"]

    assert reconciliation["startup_default_enabled"] is False

    assert reconciliation["uses_8e5_service"] is True

    schema = data["schema_safety"]

    assert schema["live_schema_activation_this_stage"] is False

    runtime = data["runtime"]

    assert runtime["runtime_py_modified"] is False

    assert runtime["main_process_activation"] is False

    assert runtime["live_bridge_injection"] is False

    assert data["next_step"] == "8E8-controlled-runtime-wiring"


def test_contract_8e6_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E8-controlled-runtime-wiring"

    validation = data["validation"]

    assert validation["baseline"] == "ddef57f"

    assert validation["isolated_tests_passed_pre_closure"] == 10

    assert validation["stage_8e_tests_passed_pre_closure"] == 78

    assert validation["trust_moderation_tests_passed_pre_closure"] == 127

    assert validation["fail_closed_runtime_tests_passed"] == 3

    assert validation["composition_reconciliation_tests_passed"] == 5

    assert validation["runtime_flag_default_off"] is True

    assert validation["schema_activation_default_authorized"] is False

    assert validation["schema_activation_explicit_permission_required"] is True

    assert validation["flag_disabled_instantiates_repositories"] is False

    assert validation["no_schema_permission_instantiates_repositories"] is False

    assert validation["authority_resolved_before_repositories"] is True

    assert validation["authority_missing_fails_before_schema"] is True

    assert validation["trust_bridge_injected_in_moderation_service"] is True

    assert validation["second_trust_write_path_created"] is False

    assert validation["reconciliation_service_composed"] is True

    assert validation["reconciliation_startup_default_off"] is True

    assert validation["runtime_py_modified"] is False

    assert validation["main_process_activation"] is False

    assert validation["live_bridge_injection"] is False

    assert validation["live_reconciliation_execution"] is False

    assert validation["live_schema_activation"] is False

    assert validation["live_database_write"] is False
