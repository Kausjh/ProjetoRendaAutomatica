from __future__ import annotations

import json
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
    ReporterCommunityModerationNaoEncontrado,
    TargetCommunityModerationNaoEncontrado,
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

CONTRACT = ROOT / "contracts" / "community_moderation_user_report_creation_v1.json"

RUNTIME = ROOT / "runtime.py"


def _conta(
    *,
    ativa: bool = True,
) -> ContaUsuario:
    return ContaUsuario(
        id="usr_test",
        email="user@example.com",
        criado_em="2026-09-22T12:00:00+00:00",
        ativa=ativa,
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


class FakeModerationRepository:
    def __init__(
        self,
        *,
        criado: bool = True,
        erro: Exception | None = None,
    ) -> None:
        self.criado = criado
        self.erro = erro
        self.calls: list[dict[str, object]] = []

    def registrar_denuncia(
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
        conta: ContaUsuario | None,
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


def _payload():
    return {
        "target_id": "disc_test",
        "motivo": "spam",
        "detalhes": "teste",
    }


def _start_server(
    *,
    repository,
    infrastructure_token: str | None = "",
):
    server = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token=infrastructure_token,
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
    user_session: str | None = None,
    infrastructure_token: str | None = None,
):
    headers = {
        "Content-Type": "application/json",
    }

    if user_session is not None:
        headers["X-User-Session"] = user_session

    if infrastructure_token is not None:
        headers["Authorization"] = f"Bearer {infrastructure_token}"

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


def test_8e10a_contract_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E10A-authenticated-report-creation"

    assert data["status"] == "completed"

    assert data["authentication"]["reporter_derived_from_session"] is True

    assert data["idempotency_boundary"]["explicit_client_idempotency_header"] is False

    assert data["readback_boundary"]["user_report_status_api"] is False


def test_inactive_account_is_rejected():
    with pytest.raises(ErroHttpUserFacing) as captured:
        _controller(FakeModerationRepository()).criar(
            _conta(ativa=False),
            _payload(),
        )

    assert captured.value.status == 401
    assert captured.value.codigo == "sessao_usuario_invalida"


@pytest.mark.parametrize(
    "field",
    [
        "reporter_conta_id",
        "target_type",
        "estado",
        "criado_em",
    ],
)
def test_authoritative_fields_cannot_be_client_supplied(
    field: str,
):
    payload = _payload()
    payload[field] = "forged"

    with pytest.raises(ErroHttpUserFacing) as captured:
        _controller(FakeModerationRepository()).criar(
            _conta(),
            payload,
        )

    assert captured.value.codigo == "payload_denuncia_invalido"


@pytest.mark.parametrize(
    "motivo",
    [
        "spam",
        "fraud",
        "malicious_link",
        "abuse",
        "off_topic",
        "duplicate",
        "other",
    ],
)
def test_all_report_reasons_are_accepted(
    motivo: str,
):
    payload = _payload()
    payload["motivo"] = motivo

    status, _ = _controller(FakeModerationRepository()).criar(
        _conta(),
        payload,
    )

    assert status == 201


def test_controller_derives_reporter_and_target_type():
    repository = FakeModerationRepository()

    status, data = _controller(repository).criar(
        _conta(),
        _payload(),
    )

    assert status == 201
    assert data["criada"] is True

    call = repository.calls[0]

    assert call["reporter_conta_id"] == "usr_test"

    assert call["target_type"] == "community_discovery"

    assert call["target_id"] == "disc_test"

    assert "reporter_conta_id" not in data["denuncia"]


def test_repository_replay_returns_200():
    status, data = _controller(FakeModerationRepository(criado=False)).criar(
        _conta(),
        _payload(),
    )

    assert status == 200
    assert data["criada"] is False


@pytest.mark.parametrize(
    "erro,status,codigo",
    [
        (
            TargetCommunityModerationNaoEncontrado("missing"),
            404,
            "target_denuncia_nao_encontrado",
        ),
        (
            ReporterCommunityModerationNaoEncontrado("missing"),
            401,
            "sessao_usuario_invalida",
        ),
        (
            ConflitoIdempotenciaCommunityModeration("conflict"),
            409,
            "conflito_denuncia",
        ),
    ],
)
def test_repository_errors_are_mapped(
    erro,
    status: int,
    codigo: str,
):
    with pytest.raises(ErroHttpUserFacing) as captured:
        _controller(FakeModerationRepository(erro=erro)).criar(
            _conta(),
            _payload(),
        )

    assert captured.value.status == status
    assert captured.value.codigo == codigo


def test_http_requires_user_session():
    repository = FakeModerationRepository()

    server, base = _start_server(repository=repository)

    try:
        status, body = _request(
            f"{base}/api/v1/me/reports",
            payload=_payload(),
        )

        assert status == 401

        assert body["erro"]["codigo"] == "sessao_usuario_obrigatoria"

        assert not repository.calls

    finally:
        server.encerrar()


def test_http_invalid_user_session_is_rejected():
    repository = FakeModerationRepository()

    server, base = _start_server(repository=repository)

    try:
        status, body = _request(
            f"{base}/api/v1/me/reports",
            payload=_payload(),
            user_session=("pra_usr_v1_invalid"),
        )

        assert status == 401

        assert body["erro"]["codigo"] == "sessao_usuario_invalida"

        assert not repository.calls

    finally:
        server.encerrar()


def test_http_authenticated_creation():
    repository = FakeModerationRepository()

    server, base = _start_server(repository=repository)

    try:
        status, body = _request(
            f"{base}/api/v1/me/reports",
            payload=_payload(),
            user_session=("pra_usr_v1_valid"),
        )

        assert status == 201

        assert body["api_version"] == "v1"

        assert body["dados"]["denuncia"]["id"] == "rpt_test"

        assert repository.calls[0]["reporter_conta_id"] == "usr_test"

    finally:
        server.encerrar()


def test_http_preserves_infrastructure_token():
    repository = FakeModerationRepository()

    server, base = _start_server(
        repository=repository,
        infrastructure_token=("infra-secret"),
    )

    try:
        status, body = _request(
            f"{base}/api/v1/me/reports",
            payload=_payload(),
            user_session=("pra_usr_v1_valid"),
        )

        assert status == 401

        assert body["erro"]["codigo"] == "infraestrutura_nao_autorizada"

        assert not repository.calls

        status_ok, _ = _request(
            f"{base}/api/v1/me/reports",
            payload=_payload(),
            user_session=("pra_usr_v1_valid"),
            infrastructure_token=("infra-secret"),
        )

        assert status_ok == 201

    finally:
        server.encerrar()


def test_http_fails_closed_without_repository():
    server, base = _start_server(repository=None)

    try:
        status, body = _request(
            f"{base}/api/v1/me/reports",
            payload=_payload(),
            user_session=("pra_usr_v1_valid"),
        )

        assert status == 503

        assert body["erro"]["codigo"] == "denuncias_comunitarias_indisponiveis"

    finally:
        server.encerrar()


def test_real_sqlite_persistence(
    tmp_path: Path,
):
    db = tmp_path / "reporting.sqlite3"

    now = "2026-09-22T12:00:00+00:00"

    identities = UserIdentityRepository(db)

    conta = identities.criar_conta(
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
        conta_id=conta.id,
        url="https://example.com/item",
        url_normalizada=("https://example.com/item"),
        url_hash="hash-disc-real",
        marketplace=None,
        agora=now,
    )

    assert created is True

    moderation = CommunityModerationRepository(db)

    controller = UserFacingCommunityReportingController(
        moderation,
        agora_provider=lambda: ("2026-09-22T12:10:00+00:00"),
    )

    status, data = controller.criar(
        conta,
        {
            "target_id": discovery.id,
            "motivo": "fraud",
            "detalhes": "Banco temporario.",
        },
    )

    assert status == 201

    report_id = str(data["denuncia"]["id"])

    persisted = moderation.obter_denuncia(report_id)

    assert persisted is not None

    assert persisted.reporter_conta_id == conta.id

    assert persisted.target_type == "community_discovery"

    assert persisted.target_id == discovery.id

    assert persisted.motivo == "fraud"

    assert persisted.estado == "received"


def test_runtime_wiring_is_gated():
    source = RUNTIME.read_text(encoding="utf-8")

    assert "community_moderation_repository_user_facing = None" in source

    assert "componentes.moderation_repository" in source

    assert "community_moderation_repository=(" in source

    assert "executar_reconciliation=False" in source


def test_8e10a_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E10B-idempotency-duplicate-protection"

    validation = data["validation"]

    assert validation["baseline_commit"] == "ed66a5d"

    assert validation["old_8e9c_http_stability_probe_runs"] == 3

    assert validation["old_8e9c_http_stability_probe_passed"] == 3

    assert validation["stage_8e9c_tests_passed"] == 21

    assert validation["isolated_8e10a_cases_passed_pre_closure"] == 25

    assert validation["stage_8e1_8e10a_cases_passed_pre_closure"] == 186

    assert validation["trust_moderation_reporting_cases_passed_pre_closure"] == 235

    assert validation["admin_server_cases_passed_pre_closure"] == 96

    assert validation["user_facing_server_cases_passed_pre_closure"] == 178

    assert validation["production_infrastructure_auth_preserved"] is True

    assert validation["user_session_required"] is True

    assert validation["reporter_derived_from_session"] is True

    assert validation["target_type_server_derived"] == "community_discovery"

    assert validation["trust_write_on_creation"] is False

    assert validation["decision_write_on_creation"] is False

    assert validation["explicit_client_idempotency_header"] is False

    assert validation["duplicate_policy_deferred_to_8e10b"] is True

    assert validation["user_status_readback_deferred_to_8e10c"] is True

    assert validation["moderation_runtime_flag_enabled"] is False

    assert validation["automatic_reconciliation_enabled"] is False

    assert validation["runtime_restart"] is False

    assert validation["live_canary"] is False

    assert validation["live_database_write"] is False

    assert validation["integrity_check"] == "ok"

    assert validation["foreign_key_errors"] == 0

    closure = data["closure"]

    assert closure["closure_test_added"] is True

    assert closure["expected_isolated_cases_after_closure"] == 26

    assert closure["expected_stage_8e1_8e10a_cases_after_closure"] == 187

    assert closure["expected_trust_moderation_reporting_cases_after_closure"] == 236

    assert closure["expected_admin_server_cases_after_closure"] == 96

    assert closure["expected_user_facing_server_cases_after_closure"] == 179
