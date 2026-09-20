from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from models.gamification import (
    PerfilGamificacao,
)
from repositories.user_identity_repository import (
    UserIdentityRepository,
)
from services.api_aplicacao.servidor import (
    ServidorApiAplicacao,
)
from services.gamification_achievements import (
    EstadoConquistaGamificacao,
)
from services.gamification_read_service import (
    LeituraGamificacaoUsuario,
    ProgressoNivelGamificacao,
)
from services.user_identity_service import (
    UserIdentityService,
)

ROOT = Path(__file__).resolve().parents[1]

CONTRACT = ROOT / "contracts" / "user_facing_api_gamification_v1.json"

RUNTIME = ROOT / "runtime.py"


class GamificationFake:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def obter(
        self,
        conta_id: str,
    ) -> LeituraGamificacaoUsuario:
        self.calls.append(conta_id)

        perfil = PerfilGamificacao(
            conta_id=conta_id,
            xp_total=140,
            reputacao_total=0,
            nivel=2,
            eventos_total=7,
            atualizado_em=("2026-09-20T10:17:01+00:00"),
        )

        progresso = ProgressoNivelGamificacao(
            nivel_atual=2,
            xp_total=140,
            xp_inicio_nivel=100,
            xp_proximo_nivel=250,
            xp_no_nivel=40,
            xp_necessario_no_nivel=150,
            xp_faltante=110,
            percentual=26.67,
            nivel_maximo=False,
        )

        conquistas = (
            EstadoConquistaGamificacao(
                codigo="radar_ligado",
                nome="Radar Ligado",
                descricao="Teste",
                badge="radar-ligado",
                desbloqueada=True,
                progresso_atual=1,
                progresso_alvo=1,
            ),
            EstadoConquistaGamificacao(
                codigo="lista_5",
                nome="Lista em Movimento",
                descricao="Teste",
                badge="lista-5",
                desbloqueada=False,
                progresso_atual=2,
                progresso_alvo=5,
            ),
        )

        return LeituraGamificacaoUsuario(
            perfil=perfil,
            progresso_nivel=progresso,
            conquistas=conquistas,
            badges_desbloqueadas=("radar-ligado",),
            ruleset_version=("gamification-reputation-" "production-v1"),
        )


def request_json(
    url: str,
    *,
    session: str | None = None,
    infra: str | None = None,
):
    headers: dict[str, str] = {}

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
            return (
                response.status,
                json.loads(response.read().decode("utf-8")),
            )

    except HTTPError as error:
        return (
            error.code,
            json.loads(error.read().decode("utf-8")),
        )


def criar_api(
    tmp_path: Path,
    *,
    infra_token: str = "",
):
    repository = UserIdentityRepository(tmp_path / "identity.sqlite3")

    identity = UserIdentityService(repository)

    conta_a = identity.criar_conta(
        email="a@example.com",
        senha="uma-senha-forte-123",
    )

    conta_b = identity.criar_conta(
        email="b@example.com",
        senha="uma-senha-forte-456",
    )

    sessao_a = identity.emitir_sessao(conta_a)

    gamification = GamificationFake()

    servidor = ServidorApiAplicacao(
        object(),  # type: ignore[arg-type]
        host="127.0.0.1",
        porta=0,
        token=infra_token,
        user_identity_service=identity,
        gamification_read_service=gamification,  # type: ignore[arg-type]
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
        gamification,
    )


def test_contract_define_get_me_gamification():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["gamification_read_http_version"] == 1

    route = data["route"]

    assert route["method"] == "GET"
    assert route["path"] == "/api/v1/me/gamification"
    assert route["requires_user_session"] is True
    assert route["identity_source"] == "X-User-Session"
    assert route["client_account_id_accepted"] is False
    assert route["writes_state"] is False


def test_gamification_exige_sessao(
    tmp_path: Path,
):
    (
        servidor,
        base,
        _,
        _,
        _,
        gamification,
    ) = criar_api(tmp_path)

    try:
        status, body = request_json(f"{base}/api/v1/me/gamification")

        assert status == 401
        assert body["erro"]["codigo"] == "sessao_usuario_obrigatoria"
        assert gamification.calls == []

    finally:
        servidor.encerrar()


def test_gamification_serializa_leitura(
    tmp_path: Path,
):
    (
        servidor,
        base,
        conta_a,
        _,
        sessao_a,
        gamification,
    ) = criar_api(tmp_path)

    try:
        status, body = request_json(
            f"{base}/api/v1/me/gamification",
            session=sessao_a.token,
        )

        assert status == 200

        dados = body["dados"]

        assert dados["perfil"]["xp_total"] == 140

        assert dados["perfil"]["nivel"] == 2

        assert dados["perfil"]["reputacao_total"] == 0

        assert dados["progresso_nivel"]["xp_proximo_nivel"] == 250

        assert dados["progresso_nivel"]["xp_faltante"] == 110

        assert dados["progresso_nivel"]["percentual"] == 26.67

        assert dados["conquistas"][0]["codigo"] == "radar_ligado"

        assert dados["badges_desbloqueadas"] == ["radar-ligado"]

        assert gamification.calls == [conta_a.id]

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
        gamification,
    ) = criar_api(tmp_path)

    try:
        status, _ = request_json(
            (f"{base}/api/v1/me/gamification" f"?conta_id={conta_b.id}"),
            session=sessao_a.token,
        )

        assert status == 200
        assert gamification.calls == [conta_a.id]

    finally:
        servidor.encerrar()


def test_gamification_preserva_bearer_infra(
    tmp_path: Path,
):
    (
        servidor,
        base,
        _,
        _,
        sessao_a,
        gamification,
    ) = criar_api(
        tmp_path,
        infra_token="segredo-infra",
    )

    try:
        sem_infra, body = request_json(
            f"{base}/api/v1/me/gamification",
            session=sessao_a.token,
        )

        assert sem_infra == 401

        assert body["erro"]["codigo"] == "infraestrutura_nao_autorizada"

        assert gamification.calls == []

        com_infra, body = request_json(
            f"{base}/api/v1/me/gamification",
            session=sessao_a.token,
            infra="segredo-infra",
        )

        assert com_infra == 200
        assert body["dados"]["perfil"]["xp_total"] == 140

    finally:
        servidor.encerrar()


def test_gamification_indisponivel_retorna_503(
    tmp_path: Path,
):
    repository = UserIdentityRepository(tmp_path / "identity.sqlite3")

    identity = UserIdentityService(repository)

    conta = identity.criar_conta(
        email="usuario@example.com",
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
            ("http://127.0.0.1:" f"{porta}" "/api/v1/me/gamification"),
            session=sessao.token,
        )

        assert status == 503

        assert body["erro"]["codigo"] == "gamificacao_indisponivel"

    finally:
        servidor.encerrar()


def test_runtime_injeta_read_service():
    source = RUNTIME.read_text(encoding="utf-8")

    assert "GamificationReadService" in source

    assert "gamification_runtime.service" in source

    assert "gamification_read_service=" "gamification_read_service" in source


def test_public_app_ainda_fora_da_6d():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["boundaries"]["public_app_integration"] is False

    assert data["boundaries"]["write_api"] is False

    assert data["boundaries"]["community_reputation"] is False
