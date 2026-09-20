from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.api_aplicacao.servidor import (
    ServidorApiAplicacao,
)
from services.mission_read_service import (
    LeituraMissaoUsuario,
    LeituraMissoesUsuario,
    LeituraRecompensaMissao,
    ResumoMissoesUsuario,
)
from services.user_identity_service import (
    UserIdentityService,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "user_facing_api_missions_v1.json"

RUNTIME = ROOT / "runtime.py"


class FakeMissionReadService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def obter(
        self,
        conta_id: str,
    ) -> LeituraMissoesUsuario:
        self.calls.append(conta_id)

        return LeituraMissoesUsuario(
            ruleset_version=("missions-community-rewards-" "production-v1"),
            instancia_chave="lifetime",
            resumo=ResumoMissoesUsuario(
                total=3,
                concluidas=1,
                em_andamento=2,
                nao_iniciadas=0,
                rewards_pending=0,
                rewards_granted=1,
            ),
            missoes=(
                LeituraMissaoUsuario(
                    codigo=("community_primeira_aprovada"),
                    titulo=("Primeira descoberta aprovada"),
                    descricao=("Tenha uma oferta aprovada."),
                    progresso_atual=1,
                    progresso_alvo=1,
                    percentual=100.0,
                    concluida=True,
                    concluida_em=("2026-09-20T14:13:26+00:00"),
                    atualizado_em=("2026-09-20T14:13:26+00:00"),
                    recompensa=(
                        LeituraRecompensaMissao(
                            tipo="xp",
                            quantidade=20,
                            status="granted",
                            concedida_em=("2026-09-20T16:33:10+00:00"),
                        )
                    ),
                ),
            ),
        )


def request_json(
    url: str,
    *,
    session: str | None = None,
    infra: str | None = None,
):
    headers = {}

    if session is not None:
        headers["X-User-Session"] = session

    if infra is not None:
        headers["Authorization"] = f"Bearer {infra}"

    request = Request(
        url,
        headers=headers,
        method="GET",
    )

    try:
        with urlopen(
            request,
            timeout=5,
        ) as response:
            status = response.status
            body = response.read()

    except HTTPError as erro:
        status = erro.code
        body = erro.read()

    return (
        status,
        json.loads(body.decode("utf-8")),
    )


def criar_api(
    tmp_path: Path,
    *,
    infra_token: str = "",
):
    repository = UserIdentityRepository(tmp_path / "identity.sqlite3")

    identity = UserIdentityService(repository)

    conta_a = identity.criar_conta(
        email="missions-a@example.com",
        senha="uma-senha-forte-123",
    )

    conta_b = identity.criar_conta(
        email="missions-b@example.com",
        senha="uma-senha-forte-123",
    )

    sessao_a = identity.emitir_sessao(conta_a)

    missions = FakeMissionReadService()

    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token=infra_token,
        user_identity_service=identity,
        mission_read_service=missions,
    )

    servidor.iniciar()

    endereco = servidor.endereco

    assert endereco is not None

    _, porta = endereco

    return (
        servidor,
        f"http://127.0.0.1:{porta}",
        conta_a,
        conta_b,
        sessao_a,
        missions,
    )


def test_contract_define_get_me_missions():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    route = data["route"]

    assert route["method"] == "GET"

    assert route["path"] == "/api/v1/me/missions"

    assert route["requires_user_session"] is True

    assert route["identity_source"] == "X-User-Session"

    assert route["client_account_id_accepted"] is False

    assert route["writes_state"] is False


def test_missions_exige_sessao(
    tmp_path: Path,
):
    (
        servidor,
        base,
        _,
        _,
        _,
        missions,
    ) = criar_api(tmp_path)

    try:
        status, body = request_json(f"{base}/api/v1/me/missions")

        assert status == 401

        assert body["erro"]["codigo"] == "sessao_usuario_obrigatoria"

        assert missions.calls == []

    finally:
        servidor.encerrar()


def test_missions_serializa_leitura(
    tmp_path: Path,
):
    (
        servidor,
        base,
        conta_a,
        _,
        sessao_a,
        missions,
    ) = criar_api(tmp_path)

    try:
        status, body = request_json(
            f"{base}/api/v1/me/missions",
            session=sessao_a.token,
        )

        assert status == 200

        dados = body["dados"]

        assert dados["ruleset_version"] == "missions-community-rewards-" "production-v1"

        assert dados["instancia_chave"] == "lifetime"

        assert dados["resumo"] == {
            "total": 3,
            "concluidas": 1,
            "em_andamento": 2,
            "nao_iniciadas": 0,
            "rewards_pending": 0,
            "rewards_granted": 1,
        }

        primeira = dados["missoes"][0]

        assert primeira["codigo"] == "community_primeira_aprovada"

        assert primeira["progresso_atual"] == 1

        assert primeira["progresso_alvo"] == 1

        assert primeira["percentual"] == 100.0

        assert primeira["concluida"] is True

        assert primeira["recompensa"] == {
            "tipo": "xp",
            "quantidade": 20,
            "status": "granted",
            "concedida_em": ("2026-09-20T16:33:10+00:00"),
        }

        assert missions.calls == [conta_a.id]

    finally:
        servidor.encerrar()


def test_conta_id_query_nao_override_sessao(
    tmp_path: Path,
):
    (
        servidor,
        base,
        conta_a,
        conta_b,
        sessao_a,
        missions,
    ) = criar_api(tmp_path)

    try:
        status, _ = request_json(
            (f"{base}/api/v1/me/missions" f"?conta_id={conta_b.id}"),
            session=sessao_a.token,
        )

        assert status == 200

        assert missions.calls == [conta_a.id]

    finally:
        servidor.encerrar()


def test_missions_preserva_bearer_infra(
    tmp_path: Path,
):
    (
        servidor,
        base,
        _,
        _,
        sessao_a,
        missions,
    ) = criar_api(
        tmp_path,
        infra_token="segredo-infra",
    )

    try:
        status, body = request_json(
            f"{base}/api/v1/me/missions",
            session=sessao_a.token,
        )

        assert status == 401

        assert body["erro"]["codigo"] == "infraestrutura_nao_autorizada"

        assert missions.calls == []

        status, body = request_json(
            f"{base}/api/v1/me/missions",
            session=sessao_a.token,
            infra="segredo-infra",
        )

        assert status == 200

        assert body["dados"]["resumo"]["total"] == 3

    finally:
        servidor.encerrar()


def test_missions_indisponiveis_retorna_503(
    tmp_path: Path,
):
    repository = UserIdentityRepository(tmp_path / "identity.sqlite3")

    identity = UserIdentityService(repository)

    conta = identity.criar_conta(
        email="missions-off@example.com",
        senha="uma-senha-forte-123",
    )

    sessao = identity.emitir_sessao(conta)

    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token="",
        user_identity_service=identity,
    )

    servidor.iniciar()

    endereco = servidor.endereco

    assert endereco is not None

    _, porta = endereco

    try:
        status, body = request_json(
            ("http://127.0.0.1:" f"{porta}" "/api/v1/me/missions"),
            session=sessao.token,
        )

        assert status == 503

        assert body["erro"]["codigo"] == "missoes_indisponiveis"

    finally:
        servidor.encerrar()


def test_runtime_injeta_mission_read_service():
    source = RUNTIME.read_text(encoding="utf-8")

    assert "MissionReadService" in source

    assert "mission_runtime.service" in source

    assert "mission_read_service=" "mission_read_service" in source


def test_contract_mantem_7f_fora_da_7e():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    boundaries = data["boundaries"]

    assert boundaries["public_app_integration"] is False

    assert boundaries["write_api"] is False

    assert boundaries["community_reputation"] is False

    assert boundaries["social_rankings"] is False
