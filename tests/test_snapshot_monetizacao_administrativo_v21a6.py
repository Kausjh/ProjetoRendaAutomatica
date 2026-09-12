from __future__ import annotations

import json
from pathlib import Path

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.controle.controlador import (
    ControladorAdministrativo,
)


def _repo(tmp_path):
    return ControleAdministrativoRepository(tmp_path / "controle_admin_v21a6.db")


def _snapshot():
    return {
        "schema_version": 1,
        "iniciado_em": "2026-09-12T12:00:00-03:00",
        "atualizado_em": "2026-09-12T12:05:00-03:00",
        "totais": {
            "processamentos": 3,
            "transformados": 2,
            "bloqueios": 1,
            "pass_through": 0,
            "retries": 1,
            "retry_minutos_total": 15,
        },
        "por_afiliador": {
            "mercado_livre": {
                "processamentos": 3,
                "transformados": 2,
                "bloqueios": 1,
                "pass_through": 0,
                "retries": 1,
                "retry_minutos_total": 15,
            }
        },
    }


def _controlador(repo):
    return ControladorAdministrativo(
        orquestrador=object(),
        fila=object(),
        verificador_chrome=lambda: True,
        repositorio_admin=repo,
    )


def test_repository_le_snapshot_monetizacao_opaco(tmp_path):
    repo = _repo(tmp_path)
    esperado = _snapshot()

    repo.definir_estado(
        "observabilidade_monetizacao_v1",
        json.dumps(
            esperado,
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    assert repo.obter_snapshot_monetizacao() == esperado


def test_repository_snapshot_monetizacao_ausente_retorna_none(
    tmp_path,
):
    repo = _repo(tmp_path)

    assert repo.obter_snapshot_monetizacao() is None


def test_repository_snapshot_monetizacao_json_invalido_retorna_none(
    tmp_path,
):
    repo = _repo(tmp_path)

    repo.definir_estado(
        "observabilidade_monetizacao_v1",
        "{json-invalido",
    )

    assert repo.obter_snapshot_monetizacao() is None


def test_repository_snapshot_monetizacao_schema_incompativel_retorna_none(
    tmp_path,
):
    repo = _repo(tmp_path)

    repo.definir_estado(
        "observabilidade_monetizacao_v1",
        json.dumps(
            {
                "schema_version": 999,
            }
        ),
    )

    assert repo.obter_snapshot_monetizacao() is None


def test_controlador_monetizacao_indisponivel_sem_repository():
    controlador = ControladorAdministrativo(
        orquestrador=object(),
        fila=object(),
        verificador_chrome=lambda: True,
        repositorio_admin=None,
    )

    assert controlador.obter_snapshot_monetizacao() == {
        "disponivel": False,
        "schema_version": 1,
        "snapshot": None,
    }


def test_controlador_expoe_snapshot_monetizacao(tmp_path):
    repo = _repo(tmp_path)
    esperado = _snapshot()

    repo.definir_estado(
        "observabilidade_monetizacao_v1",
        json.dumps(
            esperado,
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    assert _controlador(repo).obter_snapshot_monetizacao() == {
        "disponivel": True,
        "schema_version": 1,
        "snapshot": esperado,
    }


def test_rota_get_monetizacao_operacional_existe():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert 'if rota == "/monetizacao/operacional":' in fonte
    assert "controlador.obter_snapshot_monetizacao()" in fonte


def test_v21a6_nao_cria_acao_operacional_de_monetizacao():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert 'partes[0] == "monetizacao"' not in fonte


# 63.8738, -149.7525
