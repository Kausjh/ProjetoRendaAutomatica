from __future__ import annotations

import json
from pathlib import Path

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.controle.controlador import (
    ControladorAdministrativo,
)


def _snapshot():
    return {
        "schema_version": 1,
        "iniciado_em": "2026-09-12T10:00:00-03:00",
        "atualizado_em": "2026-09-12T11:00:00-03:00",
        "eventos_total": 10,
        "processamentos_total": 10,
        "transformados_total": 10,
        "bloqueios_total": 0,
        "pass_through_total": 0,
        "retries_total": 0,
        "retry_minutos_total": 0,
        "por_origem": {},
        "por_afiliador": {},
        "por_dia": {},
        "ultimo_evento_em": "2026-09-12T11:00:00-03:00",
    }


def _controlador(repo):
    return ControladorAdministrativo(
        orquestrador=object(),
        fila=object(),
        verificador_chrome=lambda: True,
        repositorio_admin=repo,
    )


def test_controlador_saude_monetizacao_indisponivel_sem_repo():
    controlador = ControladorAdministrativo(
        orquestrador=object(),
        fila=object(),
        verificador_chrome=lambda: True,
        repositorio_admin=None,
    )

    assert controlador.obter_saude_monetizacao() == {
        "disponivel": False,
        "schema_version": 1,
        "saude": None,
    }


def test_controlador_classifica_snapshot_persistido(tmp_path):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")

    repo.definir_estado(
        "observabilidade_monetizacao_v1",
        json.dumps(
            _snapshot(),
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    resposta = _controlador(repo).obter_saude_monetizacao()

    assert resposta["disponivel"] is True
    assert resposta["schema_version"] == 1
    assert resposta["saude"]["status"] == "saudavel"
    assert resposta["saude"]["amostra_suficiente"] is True


def test_rota_get_monetizacao_saude_existe():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert 'if rota == "/monetizacao/saude":' in fonte
    assert "controlador.obter_saude_monetizacao()" in fonte


def test_v21a7_preserva_endpoint_operacional_v21a6():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert 'if rota == "/monetizacao/operacional":' in fonte
    assert "controlador.obter_snapshot_monetizacao()" in fonte


def test_v21a7_rota_saude_permanece_read_only():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    inicio_get = fonte.index("            def do_GET(self) -> None:")
    inicio_post = fonte.index("            def do_POST(self) -> None:")
    trecho_get = fonte[inicio_get:inicio_post]

    assert 'if rota == "/monetizacao/saude":' in trecho_get
    assert "controlador.obter_saude_monetizacao()" in trecho_get
    assert "executar_enforcement_monetizacao" not in trecho_get
    assert "executar_acao_operacional" not in trecho_get


# 63.8738, -149.7525
