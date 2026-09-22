from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from models.community_moderation import (
    DenunciaCommunityModeration,
)
from models.user_identity import (
    ContaUsuario,
)
from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)
from repositories.community_moderation_repository import (
    CommunityModerationRepository,
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

CONTRACT = ROOT / "contracts" / "community_moderation_user_report_readback_v1.json"


def _conta(
    conta_id: str = "usr_a",
    *,
    ativa: bool = True,
) -> ContaUsuario:
    return ContaUsuario(
        id=conta_id,
        email=f"{conta_id}@example.com",
        criado_em="2026-09-22T12:00:00+00:00",
        ativa=ativa,
    )


def _report(
    report_id: str,
    *,
    reporter: str = "usr_a",
    motivo: str = "spam",
    detalhes: str | None = "detalhes privados do proprio usuario",
    estado: str = "received",
    criado_em: str = "2026-09-22T12:10:00+00:00",
    atualizado_em: str | None = None,
) -> DenunciaCommunityModeration:
    return DenunciaCommunityModeration(
        id=report_id,
        reporter_conta_id=reporter,
        target_type="community_discovery",
        target_id="disc_test",
        motivo=motivo,
        detalhes=detalhes,
        estado=estado,
        criado_em=criado_em,
        atualizado_em=(atualizado_em if atualizado_em is not None else criado_em),
    )


class FakeReadbackRepository:
    def __init__(
        self,
        reports: list[DenunciaCommunityModeration] | None = None,
    ) -> None:
        self.reports = list(reports or [])

        self.list_calls: list[dict[str, object]] = []

        self.detail_calls: list[dict[str, object]] = []

    def listar_denuncias_reporter(
        self,
        *,
        reporter_conta_id: str,
        limite: int,
        offset: int,
    ) -> list[DenunciaCommunityModeration]:
        self.list_calls.append(
            {
                "reporter_conta_id": reporter_conta_id,
                "limite": limite,
                "offset": offset,
            }
        )

        own = [report for report in self.reports if (report.reporter_conta_id == reporter_conta_id)]

        own.sort(
            key=lambda report: (
                report.criado_em,
                report.id,
            ),
            reverse=True,
        )

        return own[offset : offset + limite]

    def obter_denuncia_reporter(
        self,
        *,
        denuncia_id: str,
        reporter_conta_id: str,
    ) -> DenunciaCommunityModeration | None:
        self.detail_calls.append(
            {
                "denuncia_id": denuncia_id,
                "reporter_conta_id": reporter_conta_id,
            }
        )

        for report in self.reports:
            if report.id == denuncia_id and report.reporter_conta_id == reporter_conta_id:
                return report

        return None


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
    return UserFacingCommunityReportingController(repository)


def _start_server(
    repository,
    *,
    conta: ContaUsuario | None = None,
    infrastructure_token: str = "",
):
    server = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token=infrastructure_token,
        user_identity_service=(FakeIdentityService(conta or _conta())),  # type: ignore[arg-type]
        community_moderation_repository=repository,
    )

    server.iniciar()

    assert server._servidor is not None

    porta = int(server._servidor.server_address[1])

    return (
        server,
        f"http://127.0.0.1:{porta}",
    )


def _get(
    url: str,
    *,
    user_session: str | None = "pra_usr_v1_valid",
    infrastructure_token: str | None = None,
):
    headers: dict[
        str,
        str,
    ] = {}

    if user_session is not None:
        headers["X-User-Session"] = user_session

    if infrastructure_token is not None:
        headers["Authorization"] = f"Bearer {infrastructure_token}"

    request = Request(
        url,
        method="GET",
        headers=headers,
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
    db = tmp_path / "readback.sqlite3"

    identities = UserIdentityRepository(db)

    conta_a = identities.criar_conta(
        conta_id="usr_a",
        email_normalizado=("a@example.com"),
        email_exibicao=("a@example.com"),
        senha_salt=b"salt-a",
        senha_hash=b"hash-a",
        criado_em=("2026-09-22T12:00:00+00:00"),
    )

    conta_b = identities.criar_conta(
        conta_id="usr_b",
        email_normalizado=("b@example.com"),
        email_exibicao=("b@example.com"),
        senha_salt=b"salt-b",
        senha_hash=b"hash-b",
        criado_em=("2026-09-22T12:00:01+00:00"),
    )

    discoveries = CommunityDiscoveryRepository(db)

    discovery, created = discoveries.registrar(
        descoberta_id="disc_readback",
        conta_id=conta_a.id,
        url=("https://example.com/" "readback-item"),
        url_normalizada=("https://example.com/" "readback-item"),
        url_hash=("hash-readback-item"),
        marketplace=None,
        agora=("2026-09-22T12:01:00+00:00"),
    )

    assert created is True

    repository = CommunityModerationRepository(db)

    report_a_old = repository.registrar_denuncia_usuario(
        reporter_conta_id=conta_a.id,
        target_type="community_discovery",
        target_id=discovery.id,
        motivo="spam",
        detalhes="spam details",
        acao_idempotencia="a-spam",
        agora=("2026-09-22T12:10:00+00:00"),
    ).denuncia

    report_a_new = repository.registrar_denuncia_usuario(
        reporter_conta_id=conta_a.id,
        target_type="community_discovery",
        target_id=discovery.id,
        motivo="fraud",
        detalhes="fraud private details",
        acao_idempotencia="a-fraud",
        agora=("2026-09-22T12:11:00+00:00"),
    ).denuncia

    report_b = repository.registrar_denuncia_usuario(
        reporter_conta_id=conta_b.id,
        target_type="community_discovery",
        target_id=discovery.id,
        motivo="abuse",
        detalhes="b private details",
        acao_idempotencia="b-abuse",
        agora=("2026-09-22T12:12:00+00:00"),
    ).denuncia

    repository.registrar_decisao(
        denuncia_id=report_a_new.id,
        acao_idempotencia=("internal-decision"),
        moderator_actor_id=("radar-admin-control-plane-v1"),
        resultado="confirmed_abuse",
        familia_abuso_confirmado=("fraude_confirmada"),
        justificativa=("internal moderator justification"),
        ocorrido_em=("2026-09-22T12:13:00+00:00"),
    )

    return (
        db,
        conta_a,
        conta_b,
        report_a_old,
        report_a_new,
        report_b,
        repository,
    )


def test_8e10c_contract_boundary():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["stage"] == "8E10C-limited-user-status-readback"

    assert data["status"] == "completed"

    assert data["ownership"]["list_only_authenticated_reporter"] is True

    assert data["ownership"]["non_owned_and_missing_are_indistinguishable"] is True

    assert data["decisions"]["decision_table_queried_by_user_readback"] is False

    assert data["persistence"]["read_only_operation"] is True


def test_list_returns_only_authenticated_reporter():
    repository = FakeReadbackRepository(
        [
            _report(
                "rpt_a",
                reporter="usr_a",
            ),
            _report(
                "rpt_b",
                reporter="usr_b",
            ),
        ]
    )

    status, data = _controller(repository).listar_status(_conta("usr_a"))

    assert status == 200

    assert [item["id"] for item in data["itens"]] == ["rpt_a"]

    assert repository.list_calls[0]["reporter_conta_id"] == "usr_a"


def test_list_is_limited_projection_without_details():
    repository = FakeReadbackRepository(
        [
            _report(
                "rpt_a",
                detalhes="secret-own-details",
            ),
        ]
    )

    _, data = _controller(repository).listar_status(_conta())

    item = data["itens"][0]

    assert set(item) == {
        "id",
        "target_type",
        "target_id",
        "motivo",
        "estado",
        "criado_em",
        "atualizado_em",
    }

    assert "detalhes" not in item

    assert "reporter_conta_id" not in item


def test_detail_returns_own_details_but_no_reporter():
    repository = FakeReadbackRepository(
        [
            _report(
                "rpt_a",
                detalhes="my details",
            ),
        ]
    )

    status, data = _controller(repository).obter_status(
        _conta(),
        "rpt_a",
    )

    assert status == 200

    report = data["denuncia"]

    assert report["detalhes"] == "my details"

    assert "reporter_conta_id" not in report


def test_detail_non_owned_is_indistinguishable_404():
    repository = FakeReadbackRepository(
        [
            _report(
                "rpt_other",
                reporter="usr_b",
            ),
        ]
    )

    for report_id in (
        "rpt_other",
        "rpt_missing",
    ):
        with pytest.raises(ErroHttpUserFacing) as captured:
            _controller(repository).obter_status(
                _conta("usr_a"),
                report_id,
            )

        assert captured.value.status == 404

        assert captured.value.codigo == "denuncia_nao_encontrada"


@pytest.mark.parametrize(
    "limite,offset",
    [
        ("0", "0"),
        ("101", "0"),
        ("abc", "0"),
        ("20", "-1"),
        ("20", "abc"),
    ],
)
def test_invalid_pagination_is_400(
    limite: str,
    offset: str,
):
    with pytest.raises(ErroHttpUserFacing) as captured:
        _controller(FakeReadbackRepository()).listar_status(
            _conta(),
            limite=limite,
            offset=offset,
        )

    assert captured.value.status == 400

    assert captured.value.codigo == "paginacao_denuncias_invalida"


@pytest.mark.parametrize(
    "operation",
    [
        "list",
        "detail",
    ],
)
def test_inactive_account_is_rejected(
    operation: str,
):
    controller = _controller(FakeReadbackRepository())

    conta = _conta(ativa=False)

    with pytest.raises(ErroHttpUserFacing) as captured:

        if operation == "list":
            controller.listar_status(conta)

        else:
            controller.obter_status(
                conta,
                "rpt_x",
            )

    assert captured.value.status == 401

    assert captured.value.codigo == "sessao_usuario_invalida"


@pytest.mark.parametrize(
    "operation",
    [
        "list",
        "detail",
    ],
)
def test_repository_unavailable_fails_closed(
    operation: str,
):
    controller = _controller(None)

    with pytest.raises(ErroHttpUserFacing) as captured:

        if operation == "list":
            controller.listar_status(_conta())

        else:
            controller.obter_status(
                _conta(),
                "rpt_x",
            )

    assert captured.value.status == 503

    assert captured.value.codigo == "denuncias_comunitarias_indisponiveis"


def test_real_repository_list_filters_owner_and_orders(
    tmp_path: Path,
):
    (
        _,
        conta_a,
        _,
        report_a_old,
        report_a_new,
        _,
        repository,
    ) = _real_context(tmp_path)

    reports = repository.listar_denuncias_reporter(
        reporter_conta_id=conta_a.id,
        limite=20,
        offset=0,
    )

    assert [report.id for report in reports] == [
        report_a_new.id,
        report_a_old.id,
    ]


def test_real_repository_pagination(
    tmp_path: Path,
):
    (
        _,
        conta_a,
        _,
        report_a_old,
        _,
        _,
        repository,
    ) = _real_context(tmp_path)

    reports = repository.listar_denuncias_reporter(
        reporter_conta_id=conta_a.id,
        limite=1,
        offset=1,
    )

    assert len(reports) == 1

    assert reports[0].id == report_a_old.id


def test_real_repository_detail_enforces_owner(
    tmp_path: Path,
):
    (
        _,
        conta_a,
        conta_b,
        _,
        report_a_new,
        _,
        repository,
    ) = _real_context(tmp_path)

    own = repository.obter_denuncia_reporter(
        denuncia_id=report_a_new.id,
        reporter_conta_id=conta_a.id,
    )

    foreign = repository.obter_denuncia_reporter(
        denuncia_id=report_a_new.id,
        reporter_conta_id=conta_b.id,
    )

    assert own is not None
    assert foreign is None


def test_public_detail_does_not_leak_decision_metadata(
    tmp_path: Path,
):
    (
        _,
        conta_a,
        _,
        _,
        report_a_new,
        _,
        repository,
    ) = _real_context(tmp_path)

    status, data = _controller(repository).obter_status(
        conta_a,
        report_a_new.id,
    )

    assert status == 200

    payload = json.dumps(
        data,
        ensure_ascii=False,
    )

    for private_field in (
        "moderator_actor_id",
        "familia_abuso_confirmado",
        "justificativa",
        "chave_idempotencia",
        "reporter_conta_id",
    ):
        assert private_field not in payload

    assert "internal moderator justification" not in payload

    assert "radar-admin-control-plane-v1" not in payload

    assert "fraude_confirmada" not in payload

    assert data["denuncia"]["estado"] == "resolved"


def test_http_list_requires_user_session():
    repository = FakeReadbackRepository()

    server, base = _start_server(repository)

    try:
        status, body = _get(
            f"{base}/api/v1/me/reports",
            user_session=None,
        )

        assert status == 401

        assert body["erro"]["codigo"] == "sessao_usuario_obrigatoria"

    finally:
        server.encerrar()


def test_http_list_and_pagination():
    repository = FakeReadbackRepository(
        [
            _report(
                "rpt_1",
                criado_em=("2026-09-22T12:10:00+00:00"),
            ),
            _report(
                "rpt_2",
                motivo="fraud",
                criado_em=("2026-09-22T12:11:00+00:00"),
            ),
        ]
    )

    server, base = _start_server(repository)

    try:
        status, body = _get(f"{base}/api/v1/me/reports" "?limite=1&offset=1")

        assert status == 200

        dados = body["dados"]

        assert dados["quantidade"] == 1

        assert dados["itens"][0]["id"] == "rpt_1"

        assert "detalhes" not in dados["itens"][0]

    finally:
        server.encerrar()


def test_http_detail_own_report():
    repository = FakeReadbackRepository(
        [
            _report(
                "rpt_own",
                detalhes="visible-own-details",
            ),
        ]
    )

    server, base = _start_server(repository)

    try:
        status, body = _get(f"{base}/api/v1/me/reports/" "rpt_own")

        assert status == 200

        assert body["dados"]["denuncia"]["detalhes"] == "visible-own-details"

    finally:
        server.encerrar()


def test_http_detail_foreign_report_is_404():
    repository = FakeReadbackRepository(
        [
            _report(
                "rpt_foreign",
                reporter="usr_b",
            ),
        ]
    )

    server, base = _start_server(
        repository,
        conta=_conta("usr_a"),
    )

    try:
        status, body = _get(f"{base}/api/v1/me/reports/" "rpt_foreign")

        assert status == 404

        assert body["erro"]["codigo"] == "denuncia_nao_encontrada"

    finally:
        server.encerrar()


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/me/reports",
        "/api/v1/me/reports/rpt_own",
    ],
)
def test_http_readback_preserves_infrastructure_auth(
    path: str,
):
    repository = FakeReadbackRepository(
        [
            _report("rpt_own"),
        ]
    )

    server, base = _start_server(
        repository,
        infrastructure_token=("infra-secret"),
    )

    try:
        status, body = _get(
            f"{base}{path}",
        )

        assert status == 401

        assert body["erro"]["codigo"] == "infraestrutura_nao_autorizada"

        status_ok, _ = _get(
            f"{base}{path}",
            infrastructure_token=("infra-secret"),
        )

        assert status_ok == 200

    finally:
        server.encerrar()


def test_8e10c_final_closure_metadata():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["status"] == "completed"

    assert data["next_step"] == "8E11A-public-app-reporting-client-read-model"

    validation = data["validation"]

    assert validation["baseline_commit"] == "c6de05a"

    assert validation["pre_commit_passed"] is True

    assert validation["isolated_8e10c_cases_passed_pre_closure"] == 24

    assert validation["reporting_8e10a_8e10b_8e10c_cases_passed_pre_closure"] == 69

    assert validation["stage_8e1_8e10c_cases_passed_pre_closure"] == 230

    assert validation["trust_only_cases_passed"] == 49

    assert validation["admin_server_cases_passed"] == 96

    assert validation["user_facing_server_cases_passed_pre_closure"] == 222

    assert validation["windows_http_flake_detected"] is True

    assert validation["windows_http_flake_retry_succeeded"] is True

    assert validation["ownership_filter"] == "repository-sql"

    assert validation["list_only_own_reports"] is True

    assert validation["detail_only_own_report"] is True

    assert validation["foreign_report_status"] == 404

    assert validation["missing_report_status"] == 404

    assert validation["foreign_and_missing_indistinguishable"] is True

    assert validation["list_details_exposed"] is False

    assert validation["detail_own_details_exposed"] is True

    assert validation["reporter_id_exposed"] is False

    assert validation["idempotency_key_exposed"] is False

    assert validation["moderator_actor_exposed"] is False

    assert validation["moderation_result_exposed"] is False

    assert validation["moderator_justification_exposed"] is False

    assert validation["trust_internal_data_exposed"] is False

    assert validation["decision_table_queried_by_user_readback"] is False

    assert validation["read_only_operation"] is True

    assert validation["new_table_required"] is False

    assert validation["schema_migration_required"] is False

    assert validation["runtime_wiring_change_required"] is False

    assert validation["report_creation_changed"] is False

    assert validation["idempotency_policy_changed"] is False

    assert validation["trust_write"] is False

    assert validation["decision_write"] is False

    assert validation["public_app_ui"] is False

    assert validation["runtime_restart"] is False

    assert validation["live_canary"] is False

    assert validation["live_schema_write"] is False

    assert validation["live_database_write"] is False

    assert validation["integrity_check"] == "ok"

    assert validation["foreign_key_errors"] == 0

    closure = data["closure"]

    assert closure["closure_test_added"] is True

    assert closure["expected_isolated_8e10c_cases_after_closure"] == 25

    assert closure["expected_reporting_8e10a_8e10b_8e10c_cases_after_closure"] == 70

    assert closure["expected_stage_8e1_8e10c_cases_after_closure"] == 231

    assert closure["expected_trust_only_cases_after_closure"] == 49

    assert closure["expected_admin_server_cases_after_closure"] == 96

    assert closure["expected_user_facing_server_cases_after_closure"] == 223
