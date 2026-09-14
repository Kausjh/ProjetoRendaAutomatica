from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from repositories.user_identity_repository import UserIdentityRepository
from services.api_aplicacao.user_facing_devices import UserFacingDevicesController
from services.api_aplicacao.user_facing_http import ErroHttpUserFacing
from services.user_identity_service import UserIdentityService

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "device_registration_v1.json"
DOC = ROOT / "docs" / "34-device-registration-v1.md"
API_SERVER = ROOT / "services" / "api_aplicacao" / "servidor.py"


@pytest.fixture
def contexto(tmp_path: Path):
    banco = tmp_path / "user_identity.sqlite3"
    repository = UserIdentityRepository(banco)
    service = UserIdentityService(repository)

    conta_a = service.criar_conta(
        email="a@example.com",
        senha="senha-forte-a-123",
    )
    conta_b = service.criar_conta(
        email="b@example.com",
        senha="senha-forte-b-123",
    )

    return banco, repository, service, conta_a, conta_b


def test_contract_define_fundacao_sem_delivery_real():
    data = json.loads(CONTRACT.read_text(encoding="utf-8"))

    assert data["schema"] == "projeto-renda-automatica.device-registration"
    assert data["device_registration_version"] == 1
    assert data["stage"] == "backend-foundation"
    assert data["identity"]["source"] == "X-User-Session"
    assert data["identity"]["conta_id_from_client"] is False
    assert data["delivery"]["push_delivery_enabled"] is False
    assert data["delivery"]["push_provider_configured"] is False
    assert data["delivery"]["external_network_calls"] is False


def test_schema_cria_dispositivos_no_banco_de_identidade(contexto):
    banco, _, _, _, _ = contexto

    with sqlite3.connect(banco) as conexao:
        colunas = {
            linha[1]
            for linha in conexao.execute("PRAGMA table_info(dispositivos_usuario)").fetchall()
        }

    assert {
        "id",
        "conta_id",
        "instalacao_id",
        "plataforma",
        "push_token",
        "push_token_hash",
        "ativo",
        "criado_em",
        "atualizado_em",
        "revogado_em",
    } <= colunas


def test_multiplos_dispositivos_por_conta(contexto):
    _, _, service, conta_a, _ = contexto

    primeiro, criado_1, rotacionado_1 = service.registrar_dispositivo(
        conta_id=conta_a.id,
        instalacao_id="instalacao-a",
        plataforma="android",
        push_token="token-android-a-0001",
    )
    segundo, criado_2, rotacionado_2 = service.registrar_dispositivo(
        conta_id=conta_a.id,
        instalacao_id="instalacao-b",
        plataforma="android",
        push_token="token-android-b-0001",
    )

    assert criado_1 is True
    assert criado_2 is True
    assert rotacionado_1 is False
    assert rotacionado_2 is False
    assert primeiro.id != segundo.id
    assert len(service.listar_dispositivos_ativos(conta_a.id)) == 2


def test_rotacao_preserva_identidade_da_instalacao(contexto):
    _, _, service, conta_a, _ = contexto

    original, criado, rotacionado = service.registrar_dispositivo(
        conta_id=conta_a.id,
        instalacao_id="instalacao-a",
        plataforma="android",
        push_token="token-antigo-0001",
    )
    atualizado, criado_novamente, rotacionado_novamente = service.registrar_dispositivo(
        conta_id=conta_a.id,
        instalacao_id="instalacao-a",
        plataforma="android",
        push_token="token-novo-0002",
    )

    assert criado is True
    assert rotacionado is False
    assert criado_novamente is False
    assert rotacionado_novamente is True
    assert atualizado.id == original.id
    assert atualizado.push_token == "token-novo-0002"
    assert atualizado.ativo is True


def test_revogacao_e_reativacao(contexto):
    _, _, service, conta_a, _ = contexto

    original, _, _ = service.registrar_dispositivo(
        conta_id=conta_a.id,
        instalacao_id="instalacao-a",
        plataforma="android",
        push_token="token-reativacao-0001",
    )

    revogado = service.revogar_dispositivo(
        conta_id=conta_a.id,
        instalacao_id="instalacao-a",
    )

    assert revogado is not None
    assert revogado.id == original.id
    assert revogado.ativo is False
    assert revogado.revogado_em is not None
    assert service.listar_dispositivos_ativos(conta_a.id) == []

    reativado, criado, rotacionado = service.registrar_dispositivo(
        conta_id=conta_a.id,
        instalacao_id="instalacao-a",
        plataforma="android",
        push_token="token-reativacao-0001",
    )

    assert criado is False
    assert rotacionado is False
    assert reativado.id == original.id
    assert reativado.ativo is True
    assert reativado.revogado_em is None


def test_token_nao_pode_migrar_entre_contas(contexto):
    _, _, service, conta_a, conta_b = contexto

    service.registrar_dispositivo(
        conta_id=conta_a.id,
        instalacao_id="instalacao-a",
        plataforma="android",
        push_token="token-compartilhado-0001",
    )

    with pytest.raises(ValueError, match="outra instalacao"):
        service.registrar_dispositivo(
            conta_id=conta_b.id,
            instalacao_id="instalacao-b",
            plataforma="android",
            push_token="token-compartilhado-0001",
        )


def test_revogacao_de_outra_conta_falha_fechada(contexto):
    _, _, service, conta_a, conta_b = contexto

    service.registrar_dispositivo(
        conta_id=conta_a.id,
        instalacao_id="instalacao-a",
        plataforma="android",
        push_token="token-isolado-0001",
    )

    assert (
        service.revogar_dispositivo(
            conta_id=conta_b.id,
            instalacao_id="instalacao-a",
        )
        is None
    )
    assert len(service.listar_dispositivos_ativos(conta_a.id)) == 1


def test_controller_nao_aceita_conta_id_e_nao_expoe_token(contexto):
    _, _, service, conta_a, _ = contexto
    controller = UserFacingDevicesController(service)

    with pytest.raises(ErroHttpUserFacing) as erro:
        controller.salvar(
            conta_a,
            "instalacao-a",
            {
                "plataforma": "android",
                "push_token": "token-seguro-0001",
                "conta_id": "usr_injetado",
            },
        )

    assert erro.value.status == 400
    assert erro.value.codigo == "payload_invalido"

    status, dados = controller.salvar(
        conta_a,
        "instalacao-a",
        {
            "plataforma": "android",
            "push_token": "token-seguro-0001",
        },
    )

    assert status == 201
    assert "push_token" not in dados["dispositivo"]
    assert "token-seguro-0001" not in json.dumps(dados)


def test_controller_lista_e_revoga_so_dispositivos_da_conta(contexto):
    _, _, service, conta_a, conta_b = contexto
    controller = UserFacingDevicesController(service)

    controller.salvar(
        conta_a,
        "instalacao-a",
        {
            "plataforma": "android",
            "push_token": "token-a-0001",
        },
    )
    controller.salvar(
        conta_b,
        "instalacao-b",
        {
            "plataforma": "android",
            "push_token": "token-b-0001",
        },
    )

    status, dados = controller.listar(conta_a)
    assert status == 200
    assert [item["instalacao_id"] for item in dados["dispositivos"]] == ["instalacao-a"]

    with pytest.raises(ErroHttpUserFacing) as erro:
        controller.remover(conta_b, "instalacao-a")

    assert erro.value.status == 404


def test_application_api_expoe_apenas_rotas_me_devices():
    source = API_SERVER.read_text(encoding="utf-8")

    assert '"/api/v1/me/devices"' in source
    assert '"devices"' in source
    assert "UserFacingDevicesController" in source
    assert '"/api/v1/devices"' not in source


def test_documentacao_declara_limites_da_fase():
    texto = " ".join(DOC.read_text(encoding="utf-8").split())

    assert "sem enviar push" in texto
    assert "X-User-Session" in texto
    assert "não é devolvido pela API" in texto
    assert "aquisição automática do token no app" in texto
