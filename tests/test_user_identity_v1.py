from __future__ import annotations

import json
import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest

from repositories.user_identity_repository import UserIdentityRepository
from services.user_identity_service import UserIdentityService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "user_identity_v1.json"
DOC = ROOT / "docs" / "13-identidade-usuarios.md"


@pytest.fixture
def identity(tmp_path: Path):
    repo = UserIdentityRepository(tmp_path / "identity.sqlite3")
    service = UserIdentityService(repo)
    return repo, service


def test_contract_foundation_sem_exposicao_de_rede():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert data["schema"] == "projeto-renda-automatica.user-identity"
    assert data["identity_version"] == 1
    assert data["stage"] == "foundation"
    assert data["network_exposure"] is False


def test_contract_preserva_fronteiras():
    boundaries = json.loads(CONTRACT.read_text(encoding="utf-8"))["boundaries"]
    assert boundaries["application_api_v1_remains_read_only"] is True
    assert boundaries["admin_api_is_not_user_identity"] is True
    assert boundaries["infrastructure_bearer_is_not_user_session"] is True
    assert boundaries["telegram_publication_authority"] is False
    assert boundaries["private_android_admin_app_is_not_public_user_app"] is True


def test_cria_conta_e_normaliza_email(identity):
    _, service = identity
    conta = service.criar_conta(
        email="  Usuario@Example.COM ",
        senha="uma-senha-forte-123",
    )
    autenticada = service.autenticar(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    assert conta.id.startswith("usr_")
    assert autenticada is not None
    assert autenticada.id == conta.id


def test_email_invalido_falha(identity):
    _, service = identity
    with pytest.raises(ValueError, match="Email invalido"):
        service.criar_conta(
            email="nao-e-email",
            senha="uma-senha-forte-123",
        )


def test_senha_curta_falha(identity):
    _, service = identity
    with pytest.raises(ValueError, match="pelo menos"):
        service.criar_conta(
            email="usuario@example.com",
            senha="curta",
        )


def test_email_unico_case_insensitive(identity):
    _, service = identity
    service.criar_conta(
        email="Usuario@Example.com",
        senha="uma-senha-forte-123",
    )

    with pytest.raises(ValueError, match="Ja existe"):
        service.criar_conta(
            email="usuario@example.COM",
            senha="outra-senha-forte-456",
        )


def test_senha_incorreta_falha_fechada(identity):
    _, service = identity
    service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    assert (
        service.autenticar(
            email="usuario@example.com",
            senha="senha-errada-999",
        )
        is None
    )


def test_senha_nao_e_persistida_em_texto_puro(tmp_path: Path):
    banco = tmp_path / "identity.sqlite3"
    repo = UserIdentityRepository(banco)
    service = UserIdentityService(repo)
    senha = "segredo-unico-123456"
    service.criar_conta(email="usuario@example.com", senha=senha)

    raw = banco.read_bytes()
    assert senha.encode("utf-8") not in raw


def test_salts_sao_individuais(tmp_path: Path):
    banco = tmp_path / "identity.sqlite3"
    repo = UserIdentityRepository(banco)
    service = UserIdentityService(repo)
    senha = "mesma-senha-forte-123"

    service.criar_conta(email="a@example.com", senha=senha)
    service.criar_conta(email="b@example.com", senha=senha)

    with sqlite3.connect(banco) as conexao:
        rows = conexao.execute(
            "SELECT senha_salt, senha_hash FROM contas_usuario ORDER BY email_normalizado"
        ).fetchall()

    assert rows[0][0] != rows[1][0]
    assert rows[0][1] != rows[1][1]


def test_emite_e_resolve_sessao(identity):
    _, service = identity
    conta = service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    emitida = service.emitir_sessao(conta)
    resolvida = service.resolver_sessao(emitida.token)

    assert emitida.token.startswith("pra_usr_v1_")
    assert emitida.sessao.id.startswith("ses_")
    assert resolvida is not None
    assert resolvida.id == conta.id


def test_token_de_sessao_nao_e_persistido_em_texto_puro(tmp_path: Path):
    banco = tmp_path / "identity.sqlite3"
    repo = UserIdentityRepository(banco)
    service = UserIdentityService(repo)
    conta = service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    emitida = service.emitir_sessao(conta)

    assert emitida.token.encode("utf-8") not in banco.read_bytes()


def test_token_aleatorio_por_sessao(identity):
    _, service = identity
    conta = service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    primeira = service.emitir_sessao(conta)
    segunda = service.emitir_sessao(conta)

    assert primeira.token != segunda.token
    assert primeira.sessao.id != segunda.sessao.id


def test_revogacao_invalida_sessao(identity):
    _, service = identity
    conta = service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    emitida = service.emitir_sessao(conta)

    assert service.revogar_sessao(emitida.token) is True
    assert service.resolver_sessao(emitida.token) is None
    assert service.revogar_sessao(emitida.token) is False


def test_sessao_expirada_falha_fechada(tmp_path: Path):
    repo = UserIdentityRepository(tmp_path / "identity.sqlite3")
    service = UserIdentityService(
        repo,
        session_ttl=timedelta(microseconds=1),
    )
    conta = service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    emitida = service.emitir_sessao(conta)

    assert service.resolver_sessao(emitida.token) is None


def test_autenticar_e_emitir_sessao(identity):
    _, service = identity
    conta = service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    emitida = service.autenticar_e_emitir_sessao(
        email="USUARIO@example.com",
        senha="uma-senha-forte-123",
    )

    assert emitida is not None
    assert emitida.conta.id == conta.id
    assert service.resolver_sessao(emitida.token) is not None


def test_login_invalido_nao_emite_sessao(identity):
    _, service = identity
    service.criar_conta(
        email="usuario@example.com",
        senha="uma-senha-forte-123",
    )
    assert (
        service.autenticar_e_emitir_sessao(
            email="usuario@example.com",
            senha="senha-errada-999",
        )
        is None
    )


def test_documentacao_declara_separacao_de_dominios():
    texto = DOC.read_text(encoding="utf-8")
    texto_normalizado = " ".join(texto.split())

    assert "não cria rotas HTTP" in texto_normalizado
    assert "Application API V1 permanece read-only" in texto_normalizado
    assert "credencial de infraestrutura" in texto_normalizado
    assert "não representa identidade pública" in texto_normalizado
