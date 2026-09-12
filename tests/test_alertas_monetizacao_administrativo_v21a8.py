from __future__ import annotations

import json
from pathlib import Path

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.controle.controlador import (
    ControladorAdministrativo,
)


def _snapshot_critico():
    return {
        "schema_version": 1,
        "iniciado_em": "2026-09-12T10:00:00-03:00",
        "atualizado_em": "2026-09-12T11:00:00-03:00",
        "eventos_total": 10,
        "processamentos_total": 10,
        "transformados_total": 6,
        "bloqueios_total": 4,
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


def test_controlador_alertas_indisponivel_sem_repo():
    controlador = ControladorAdministrativo(
        orquestrador=object(),
        fila=object(),
        verificador_chrome=lambda: True,
        repositorio_admin=None,
    )

    assert controlador.obter_alertas_monetizacao() == {
        "disponivel": False,
        "schema_version": 1,
        "alertas": None,
    }


def test_controlador_expoe_alerta_critico(tmp_path):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")

    repo.definir_estado(
        "observabilidade_monetizacao_v1",
        json.dumps(
            _snapshot_critico(),
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    resposta = _controlador(repo).obter_alertas_monetizacao()

    assert resposta["disponivel"] is True

    alertas = resposta["alertas"]

    assert alertas["alertas_total"] == 1
    assert alertas["criticos_total"] == 1
    assert alertas["alertas"][0]["codigo"] == "taxa_bloqueio_critica"


def test_rota_get_monetizacao_alertas_existe():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert 'if rota == "/monetizacao/alertas":' in fonte
    assert "controlador.obter_alertas_monetizacao()" in fonte


def test_v21a8_preserva_rotas_anteriores():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert 'if rota == "/monetizacao/operacional":' in fonte
    assert 'if rota == "/monetizacao/saude":' in fonte


def test_v21a8_rota_alertas_permanece_read_only():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    inicio_get = fonte.index("            def do_GET(self) -> None:")
    inicio_post = fonte.index("            def do_POST(self) -> None:")
    trecho_get = fonte[inicio_get:inicio_post]

    assert 'if rota == "/monetizacao/alertas":' in trecho_get
    assert "controlador.obter_alertas_monetizacao()" in trecho_get
    assert "executar_enforcement_monetizacao" not in trecho_get
    assert "executar_acao_operacional" not in trecho_get


def test_gerador_nao_importa_telegram():
    fonte = Path("services/gerador_alertas_monetizacao.py").read_text(encoding="utf-8-sig")

    assert "TelegramBot" not in fonte
    assert "send_message" not in fonte
    assert "enviar_mensagem" not in fonte


def test_gerador_nao_persiste_estado():
    fonte = Path("services/gerador_alertas_monetizacao.py").read_text(encoding="utf-8-sig")

    assert "definir_estado" not in fonte
    assert "registrar_auditoria" not in fonte
    assert "sqlite" not in fonte.lower()


# 63.8738, -149.7525
