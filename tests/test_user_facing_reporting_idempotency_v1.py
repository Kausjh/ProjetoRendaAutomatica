from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from models.community_moderation import (
    DenunciaCommunityModeration,
    ResultadoRegistroDenunciaCommunityModeration,
)
from models.user_identity import ContaUsuario
from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.community_moderation_repository import (
    CommunityModerationRepository,
    ConflitoIdempotenciaCommunityModeration,
    DuplicataDenunciaCommunityModeration,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.api_aplicacao.servidor import (
    ServidorApiAplicacao,
)
from services.api_aplicacao.user_facing_http import (
    ErroHttpUserFacing,
)
from services.api_aplicacao.user_facing_reporting import (
    UserFacingCommunityReportingController,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "community_moderation_user_report_idempotency_v1.json"


def _conta(
    conta_id: str = "usr_test",
) -> ContaUsuario:
    return ContaUsuario(
        id=conta_id,
        email=(f"{conta_id}@example.com"),
        criado_em="2026-09-22T12:00:00+00:00",
        ativa=True,
    )


def _denuncia() -> DenunciaCommunityModeration:
    return DenunciaCommunityModeration(
        id="rpt_test",
        reporter_conta_id="usr_test",
        target_type="community_discovery",
        target_id="disc_test",
        motivo="spam",
        detalhes="teste",
        estado="received",
        criado_em="2026-09-22T12:10:00+00:00",
        atualizado_em="2026-09-22T12:10:00+00:00",
    )


class FakeIdempotentRepository:
    def __init__(
        self,
        *,
        criado: bool = True,
        erro: Exception | None = None,
    ) -> None:
        self.criado = criado
        self.erro = erro
        self.calls: list[dict[str, object]] = []

    def registrar_denuncia_usuario(
        self,
        **kwargs,
    ):
        self.calls.append(dict(kwargs))

        if self.erro is not None:
            raise self.erro

        return ResultadoRegistroDenunciaCommunityModeration(
            denuncia=_denuncia(),
            criado=self.criado,
        )


class FakeIdentityService:
    def __init__(
        self,
        conta: ContaUsuario,
    ) -> None:
        self.conta = conta

    def resolver_sessao(
        self,
        token: str,
    ) -> ContaUsuario | None:
        if token != "pra_usr_v1_valid":
            return None

        return self.conta


def _controller(
    repository,
):
    return UserFacingCommunityReportingController(
        repository,
        agora_provider=lambda: ("2026-09-22T12:10:00+00:00"),
    )


def _payload(
    *,
    target_id: str = "disc_test",
    motivo: str = "spam",
    detalhes: str | None = "teste",
):
    return {
        "target_id": target_id,
        "motivo": motivo,
        "detalhes": detalhes,
    }


def _start_server(
    repository,
):
    server = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="",
        user_identity_service=FakeIdentityService(_conta()),  # type: ignore[arg-type]
        community_moderation_repository=repository,
    )

    server.iniciar()

    assert server._servidor is not None

    porta = int(server._servidor.server_address[1])

    return (
        server,
        f"http://127.0.0.1:{porta}",
    )


def _request(
    url: str,
    *,
    payload: object,
    idempotency_key: str | None,
):
    headers = {
        "Content-Type": "application/json",
        "X-User-Session": "pra_usr_v1_valid",
    }

    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key

    request = Request(
        url,
        method="POST",
        headers=headers,
        data=json.dumps(payload).encode("utf-8"),
    )

    try:
        with urlopen(
            request,
            timeout=5,
        ) as response:
            return (
                response.status,
                json.loads(response.read().decode("utf-8")),
            )

    except HTTPError as error:
        return (
            error.code,
            json.loads(error.read().decode("utf-8")),
        )


def _real_context(
    tmp_path: Path,
):
    db = tmp_path / "idempotency.sqlite3"

    now = "2026-09-22T12:00:00+00:00"

    identities = UserIdentityRepository(db)

    reporter = identities.criar_conta(
        conta_id="usr_real",
        email_normalizado=("real@example.com"),
        email_exibicao=("real@example.com"),
        senha_salt=b"salt",
        senha_hash=b"hash",
        criado_em=now,
    )

    discoveries = CommunityDiscoveryRepository(db)

    discovery, created = discoveries.registrar(
        descoberta_id="disc_real",
        conta_id=reporter.id,
        url="https://example.com/item",
        url_normalizada=("https://example.com/item"),
        url_hash="hash-disc-real",
        marketplace=None,
        agora=now,
    )

    assert created is True

    repository = CommunityModerationRepository(db)

    return (
        db,
        identities,
        reporter,
        discovery,
        repository,
    )


def test_8e10b_contract_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E10B-idempotency-duplicate-protection"

    assert data["status"] == "completed"

    assert data["route"]["idempotency_header_required"] is True

    assert data["persistence"]["new_table_required"] is False

    assert data["boundaries"]["user_status_readback"] is False


def test_controller_requires_idempotency_key():
    repository = FakeIdempotentRepository()

    with pytest.raises(ErroHttpUserFacing) as captured:
        _controller(repository).criar_idempotente(
            _conta(),
            _payload(),
            idempotency_key=None,
        )

    assert captured.value.status == 400

    assert captured.value.codigo == "idempotency_key_obrigatoria"

    assert not repository.calls


@pytest.mark.parametrize(
    "key",
    [
        "key with spaces",
        "chave/nao-permitida",
        "ç",
        "x" * 129,
    ],
)
def test_controller_rejects_invalid_idempotency_key(
    key: str,
):
    repository = FakeIdempotentRepository()

    with pytest.raises(ErroHttpUserFacing) as captured:
        _controller(repository).criar_idempotente(
            _conta(),
            _payload(),
            idempotency_key=key,
        )

    assert captured.value.status == 400

    assert captured.value.codigo == "idempotency_key_invalida"

    assert not repository.calls


def test_controller_passes_key_to_repository():
    repository = FakeIdempotentRepository()

    status, data = _controller(repository).criar_idempotente(
        _conta(),
        _payload(),
        idempotency_key="report-key-1",
    )

    assert status == 201

    assert data["idempotent_replay"] is False

    assert repository.calls[0]["acao_idempotencia"] == "report-key-1"


def test_controller_exact_replay_returns_200():
    status, data = _controller(FakeIdempotentRepository(criado=False)).criar_idempotente(
        _conta(),
        _payload(),
        idempotency_key="report-key-1",
    )

    assert status == 200

    assert data["criada"] is False

    assert data["idempotent_replay"] is True


@pytest.mark.parametrize(
    "erro,codigo",
    [
        (
            ConflitoIdempotenciaCommunityModeration("conflict"),
            "idempotency_key_reutilizada",
        ),
        (
            DuplicataDenunciaCommunityModeration("duplicate"),
            "denuncia_duplicada",
        ),
    ],
)
def test_controller_maps_idempotency_conflicts(
    erro: Exception,
    codigo: str,
):
    with pytest.raises(ErroHttpUserFacing) as captured:
        _controller(FakeIdempotentRepository(erro=erro)).criar_idempotente(
            _conta(),
            _payload(),
            idempotency_key="report-key-1",
        )

    assert captured.value.status == 409

    assert captured.value.codigo == codigo


def test_http_missing_idempotency_key_is_400():
    repository = FakeIdempotentRepository()

    server, base = _start_server(repository)

    try:
        status, body = _request(
            f"{base}/api/v1/me/reports",
            payload=_payload(),
            idempotency_key=None,
        )

        assert status == 400

        assert body["erro"]["codigo"] == "idempotency_key_obrigatoria"

        assert not repository.calls

    finally:
        server.encerrar()


def test_http_invalid_idempotency_key_is_400():
    repository = FakeIdempotentRepository()

    server, base = _start_server(repository)

    try:
        status, body = _request(
            f"{base}/api/v1/me/reports",
            payload=_payload(),
            idempotency_key="invalid key",
        )

        assert status == 400

        assert body["erro"]["codigo"] == "idempotency_key_invalida"

        assert not repository.calls

    finally:
        server.encerrar()


def test_http_exact_replay_is_200():
    repository = FakeIdempotentRepository(criado=False)

    server, base = _start_server(repository)

    try:
        status, body = _request(
            f"{base}/api/v1/me/reports",
            payload=_payload(),
            idempotency_key="report-key-1",
        )

        assert status == 200

        assert body["dados"]["idempotent_replay"] is True

    finally:
        server.encerrar()


def test_real_repository_exact_replay_creates_one_row(
    tmp_path: Path,
):
    (
        db,
        _,
        reporter,
        discovery,
        repository,
    ) = _real_context(tmp_path)

    first = repository.registrar_denuncia_usuario(
        reporter_conta_id=reporter.id,
        target_type="community_discovery",
        target_id=discovery.id,
        motivo="spam",
        detalhes="same",
        acao_idempotencia="same-key",
        agora="2026-09-22T12:10:00+00:00",
    )

    second = repository.registrar_denuncia_usuario(
        reporter_conta_id=reporter.id,
        target_type="community_discovery",
        target_id=discovery.id,
        motivo="spam",
        detalhes="same",
        acao_idempotencia="same-key",
        agora="2026-09-22T12:11:00+00:00",
    )

    assert first.criado is True
    assert second.criado is False

    assert first.denuncia.id == second.denuncia.id

    with sqlite3.connect(db) as conn:
        count = int(
            conn.execute("SELECT COUNT(*) " "FROM community_moderation_reports").fetchone()[0]
        )

    assert count == 1


def test_real_repository_same_key_different_payload_conflicts(
    tmp_path: Path,
):
    (
        _,
        _,
        reporter,
        discovery,
        repository,
    ) = _real_context(tmp_path)

    repository.registrar_denuncia_usuario(
        reporter_conta_id=reporter.id,
        target_type="community_discovery",
        target_id=discovery.id,
        motivo="spam",
        detalhes="first",
        acao_idempotencia="same-key",
        agora="2026-09-22T12:10:00+00:00",
    )

    with pytest.raises(ConflitoIdempotenciaCommunityModeration):
        repository.registrar_denuncia_usuario(
            reporter_conta_id=reporter.id,
            target_type="community_discovery",
            target_id=discovery.id,
            motivo="spam",
            detalhes="changed",
            acao_idempotencia="same-key",
            agora="2026-09-22T12:11:00+00:00",
        )


def test_real_repository_different_key_same_semantics_is_duplicate(
    tmp_path: Path,
):
    (
        db,
        _,
        reporter,
        discovery,
        repository,
    ) = _real_context(tmp_path)

    repository.registrar_denuncia_usuario(
        reporter_conta_id=reporter.id,
        target_type="community_discovery",
        target_id=discovery.id,
        motivo="fraud",
        detalhes="first",
        acao_idempotencia="key-one",
        agora="2026-09-22T12:10:00+00:00",
    )

    with pytest.raises(DuplicataDenunciaCommunityModeration):
        repository.registrar_denuncia_usuario(
            reporter_conta_id=reporter.id,
            target_type="community_discovery",
            target_id=discovery.id,
            motivo="fraud",
            detalhes="second",
            acao_idempotencia="key-two",
            agora="2026-09-22T12:11:00+00:00",
        )

    with sqlite3.connect(db) as conn:
        count = int(
            conn.execute("SELECT COUNT(*) " "FROM community_moderation_reports").fetchone()[0]
        )

    assert count == 1


def test_real_repository_same_key_is_scoped_by_reporter(
    tmp_path: Path,
):
    (
        db,
        identities,
        reporter_a,
        discovery,
        repository,
    ) = _real_context(tmp_path)

    reporter_b = identities.criar_conta(
        conta_id="usr_second",
        email_normalizado=("second@example.com"),
        email_exibicao=("second@example.com"),
        senha_salt=b"salt2",
        senha_hash=b"hash2",
        criado_em=("2026-09-22T12:00:00+00:00"),
    )

    first = repository.registrar_denuncia_usuario(
        reporter_conta_id=reporter_a.id,
        target_type="community_discovery",
        target_id=discovery.id,
        motivo="abuse",
        detalhes=None,
        acao_idempotencia="shared-key",
        agora="2026-09-22T12:10:00+00:00",
    )

    second = repository.registrar_denuncia_usuario(
        reporter_conta_id=reporter_b.id,
        target_type="community_discovery",
        target_id=discovery.id,
        motivo="abuse",
        detalhes=None,
        acao_idempotencia="shared-key",
        agora="2026-09-22T12:11:00+00:00",
    )

    assert first.criado is True
    assert second.criado is True

    assert first.denuncia.id != second.denuncia.id

    with sqlite3.connect(db) as conn:
        count = int(
            conn.execute("SELECT COUNT(*) " "FROM community_moderation_reports").fetchone()[0]
        )

    assert count == 2


def test_real_report_creation_does_not_create_decision(
    tmp_path: Path,
):
    (
        db,
        _,
        reporter,
        discovery,
        repository,
    ) = _real_context(tmp_path)

    repository.registrar_denuncia_usuario(
        reporter_conta_id=reporter.id,
        target_type="community_discovery",
        target_id=discovery.id,
        motivo="malicious_link",
        detalhes=None,
        acao_idempotencia="decision-check",
        agora="2026-09-22T12:10:00+00:00",
    )

    with sqlite3.connect(db) as conn:
        decisions = int(
            conn.execute("SELECT COUNT(*) " "FROM community_moderation_decisions").fetchone()[0]
        )

    assert decisions == 0


def test_8e10b_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E10C-limited-user-status-readback"

    validation = data["validation"]

    assert validation["baseline_commit"] == "ddf9e7e"

    assert validation["structural_ast_audit_passed"] is True

    assert validation["pre_commit_passed"] is True

    assert validation["isolated_8e10b_cases_passed_pre_closure"] == 18

    assert validation["stage_8e10a_regression_cases_passed"] == 26

    assert validation["stage_8e1_8e10b_cases_passed_pre_closure"] == 205

    assert validation["trust_moderation_reporting_cases_passed_pre_closure"] == 254

    assert validation["admin_server_cases_passed"] == 96

    assert validation["user_facing_server_cases_passed_pre_closure"] == 197

    assert validation["idempotency_header"] == "Idempotency-Key"

    assert validation["idempotency_header_required"] is True

    assert validation["idempotency_scope"] == "authenticated-reporter"

    assert validation["first_creation_status"] == 201

    assert validation["exact_replay_status"] == 200

    assert validation["same_key_different_payload_status"] == 409

    assert validation["different_key_same_semantics_status"] == 409

    assert validation["cross_reporter_same_key_allowed"] is True

    assert validation["new_table_required"] is False

    assert validation["schema_migration_required"] is False

    assert validation["legacy_registrar_denuncia_preserved"] is True

    assert validation["user_status_readback"] is False

    assert validation["user_status_readback_deferred_to_8e10c"] is True

    assert validation["trust_write"] is False

    assert validation["decision_write"] is False

    assert validation["moderation_runtime_flag_enabled"] is False

    assert validation["automatic_reconciliation_enabled"] is False

    assert validation["runtime_restart"] is False

    assert validation["live_canary"] is False

    assert validation["live_schema_write"] is False

    assert validation["live_database_write"] is False

    assert validation["integrity_check"] == "ok"

    assert validation["foreign_key_errors"] == 0

    closure = data["closure"]

    assert closure["closure_test_added"] is True

    assert closure["expected_isolated_8e10b_cases_after_closure"] == 19

    assert closure["expected_stage_8e1_8e10b_cases_after_closure"] == 206

    assert closure["expected_trust_moderation_reporting_cases_after_closure"] == 255

    assert closure["expected_admin_server_cases_after_closure"] == 96

    assert closure["expected_user_facing_server_cases_after_closure"] == 198
