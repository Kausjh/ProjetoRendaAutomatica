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


def test_controlador_shadow_indisponivel_sem_repo():
    controlador = ControladorAdministrativo(
        orquestrador=object(),
        fila=object(),
        verificador_chrome=lambda: True,
        repositorio_admin=None,
    )

    assert controlador.obter_recomendacao_shadow_monetizacao() == {
        "disponivel": False,
        "schema_version": 1,
        "shadow": None,
    }


def test_controlador_expoe_recomendacao_shadow(tmp_path):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")

    repo.definir_estado(
        "observabilidade_monetizacao_v1",
        json.dumps(
            _snapshot_critico(),
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    resposta = _controlador(repo).obter_recomendacao_shadow_monetizacao()

    assert resposta["disponivel"] is True

    shadow = resposta["shadow"]

    assert shadow["modo"] == "shadow"
    assert shadow["acao_sugerida_principal"] == "considerar_pausa_publicador"
    assert shadow["autoridade_operacional"] is False
    assert shadow["executa_automaticamente"] is False
    assert shadow["recomendacoes"][0]["executavel"] is False
    assert shadow["recomendacoes"][0]["executada"] is False


def test_rota_get_monetizacao_shadow_existe():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert 'if rota == "/monetizacao/shadow":' in fonte
    assert "controlador." "obter_recomendacao_shadow_monetizacao()" in fonte


def test_v21a9_preserva_rotas_anteriores():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert 'if rota == "/monetizacao/operacional":' in fonte
    assert 'if rota == "/monetizacao/saude":' in fonte
    assert 'if rota == "/monetizacao/alertas":' in fonte


def test_v21a9_nao_cria_post_de_monetizacao():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert 'partes[0] == "monetizacao"' not in fonte


def test_recomendador_nao_importa_superficies_operacionais():
    fonte = Path("services/recomendador_shadow_monetizacao.py").read_text(encoding="utf-8-sig")

    proibidos = (
        "executar_acao_operacional",
        "pausar_publicador(",
        "suspender_servicos_telegram(",
        "TelegramBot",
        "send_message",
        "enviar_mensagem",
        "definir_estado",
        "registrar_auditoria",
        "CircuitBreaker",
        "kill_switch",
    )

    for termo in proibidos:
        assert termo not in fonte


def test_controlador_shadow_nao_chama_executor_operacional():
    fonte = Path("services/controle/controlador.py").read_text(encoding="utf-8-sig")

    inicio = fonte.index("    def obter_recomendacao_shadow_monetizacao(")
    resto = fonte[inicio:]

    proximo = resto.find(
        "\n    def ",
        10,
    )

    trecho = resto if proximo == -1 else resto[:proximo]

    assert "executar_acao_operacional" not in trecho
    assert "pausar_publicador" not in trecho
    assert "orquestrador." not in trecho


# 63.8738, -149.7525
