from __future__ import annotations

from pathlib import Path

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.controle.controlador import (
    ControladorAdministrativo,
)
from services.reconciliador_enforcement_monetizacao import (
    classificar_reserva_enforcement,
    confirmacao_consumo_esperada,
    confirmacao_reconciliacao_esperada,
)


def _reserva(recomendacao_id: str):
    return {
        "recomendacao_id": recomendacao_id,
        "status": "reservado",
        "reservado_em": "2026-09-12T12:00:00-03:00",
        "concluido_em": None,
    }


def _controlador(tmp_path):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")
    controlador = object.__new__(ControladorAdministrativo)
    controlador.repositorio_admin = repo
    return controlador, repo


def test_segmento_mesmo_id_e_evidencia_forte():
    rid = "shadow:monetizacao:origem:" "amazon:critica:" "considerar_isolamento_origem"

    diagnostico = classificar_reserva_enforcement(
        reserva=_reserva(rid),
        segmento={
            "escopo": "origem",
            "alvo": "amazon",
            "ativo": True,
            "recomendacao_id": rid,
        },
        publicador_pausado=False,
        auditoria_pausa_sucesso=False,
    )

    assert diagnostico["evidencia_forte"] is True
    assert diagnostico["pode_concluir"] is True
    assert diagnostico["libera_replay"] is False


def test_global_pausado_e_evidencia_forte():
    rid = "shadow:monetizacao:global:" "geral:critica:" "considerar_pausa_publicador"

    diagnostico = classificar_reserva_enforcement(
        reserva=_reserva(rid),
        segmento=None,
        publicador_pausado=True,
        auditoria_pausa_sucesso=False,
    )

    assert diagnostico["pode_concluir"] is True
    assert diagnostico["tipo_evidencia"] == "estado_publicador_pausado"


def test_ambiguo_exige_revisao_manual():
    diagnostico = classificar_reserva_enforcement(
        reserva=_reserva("rid-ambiguo"),
        segmento=None,
        publicador_pausado=False,
        auditoria_pausa_sucesso=False,
    )

    assert diagnostico["pode_concluir"] is False
    assert diagnostico["motivo"] == "revisao_manual"


def test_conclusao_e_idempotente(tmp_path):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")
    rid = "rid-idempotente"

    assert repo.reservar_enforcement_monetizacao(rid) is True
    assert repo.concluir_enforcement_monetizacao(rid) is True
    assert repo.concluir_enforcement_monetizacao(rid) is True

    estado = repo.obter_enforcement_monetizacao_consumido(rid)
    assert estado is not None
    assert estado["status"] == "concluido"


def test_listagem_retorna_so_reservados(tmp_path):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")

    assert repo.reservar_enforcement_monetizacao("rid-a") is True
    assert repo.reservar_enforcement_monetizacao("rid-b") is True
    assert repo.concluir_enforcement_monetizacao("rid-b") is True

    itens = repo.listar_enforcement_monetizacao_reservados()

    assert [item["recomendacao_id"] for item in itens] == ["rid-a"]


def test_reconciliacao_segmentada_conclui_sem_replay(
    tmp_path,
):
    controlador, repo = _controlador(tmp_path)
    rid = "shadow:monetizacao:origem:" "amazon:critica:" "considerar_isolamento_origem"

    assert repo.reservar_enforcement_monetizacao(rid) is True

    repo.definir_enforcement_segmento_monetizacao(
        escopo="origem",
        alvo="amazon",
        ativo=True,
        recomendacao_id=rid,
    )

    resposta = controlador.reconciliar_reserva_enforcement_monetizacao(
        recomendacao_id=rid,
        confirmacao=(confirmacao_reconciliacao_esperada(rid)),
        dispositivo="pytest",
    )

    assert resposta["executado"] is True
    assert resposta["libera_replay"] is False

    estado = repo.obter_enforcement_monetizacao_consumido(rid)
    assert estado is not None
    assert estado["status"] == "concluido"
    assert repo.reservar_enforcement_monetizacao(rid) is False


def test_reconciliacao_ambigua_nao_muda_reserva(
    tmp_path,
):
    controlador, repo = _controlador(tmp_path)
    rid = "rid-ambiguo"

    assert repo.reservar_enforcement_monetizacao(rid) is True

    resposta = controlador.reconciliar_reserva_enforcement_monetizacao(
        recomendacao_id=rid,
        confirmacao=(confirmacao_reconciliacao_esperada(rid)),
        dispositivo="pytest",
    )

    assert resposta["executado"] is False
    assert resposta["motivo"] == "evidencia_insuficiente_revisao_manual"

    estado = repo.obter_enforcement_monetizacao_consumido(rid)
    assert estado is not None
    assert estado["status"] == "reservado"


def test_consumo_manual_fecha_ambiguo_sem_replay(
    tmp_path,
):
    controlador, repo = _controlador(tmp_path)
    rid = "rid-manual"

    assert repo.reservar_enforcement_monetizacao(rid) is True

    resposta = controlador.consumir_reserva_enforcement_sem_replay(
        recomendacao_id=rid,
        confirmacao=(confirmacao_consumo_esperada(rid)),
        dispositivo="pytest",
    )

    assert resposta["executado"] is True
    assert resposta["libera_replay"] is False
    assert repo.reservar_enforcement_monetizacao(rid) is False


def test_confirmacao_invalida_nao_consumira_reserva(
    tmp_path,
):
    controlador, repo = _controlador(tmp_path)
    rid = "rid-confirmacao"

    assert repo.reservar_enforcement_monetizacao(rid) is True

    resposta = controlador.consumir_reserva_enforcement_sem_replay(
        recomendacao_id=rid,
        confirmacao="NAO_CONFIRMADO",
        dispositivo="pytest",
    )

    assert resposta["executado"] is False

    estado = repo.obter_enforcement_monetizacao_consumido(rid)
    assert estado is not None
    assert estado["status"] == "reservado"


def test_v21a13_nao_libera_reserva_para_replay():
    fonte = Path("services/controle/controlador.py").read_text(encoding="utf-8-sig")

    inicio = fonte.index("def reconciliar_reserva_enforcement_monetizacao")
    fim = fonte.index(
        "def consumir_reserva_enforcement_sem_replay",
        inicio,
    )
    trecho_reconciliar = fonte[inicio:fim]

    inicio_consumo = fim
    proximo = fonte.find(
        "\n    def ",
        inicio_consumo + 8,
    )
    trecho_consumo = fonte[inicio_consumo:proximo] if proximo != -1 else fonte[inicio_consumo:]

    assert "liberar_enforcement_monetizacao" not in trecho_reconciliar
    assert "liberar_enforcement_monetizacao" not in trecho_consumo


def test_v21a13_sem_ttl_automatico():
    fonte = Path("services/reconciliador_enforcement_monetizacao.py").read_text(
        encoding="utf-8-sig"
    )

    assert "timedelta" not in fonte
    assert "time.time" not in fonte
    assert '"ttl_automatico": False' in fonte


def test_rotas_v21a13_e_fail_closed_preservado():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert '"/monetizacao/enforcement/reservas"' in fonte
    assert '"reconciliar"' in fonte
    assert '"consumir-reserva"' in fonte

    inicio = fonte.index("def do_POST")
    trecho_post = fonte[inicio : inicio + 2200]

    assert '"/monetizacao/enforcement/"' in trecho_post
    assert "and not token_administrativo" in trecho_post
    assert "503" in trecho_post


def test_get_reservas_e_read_only():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    inicio = fonte.index('if rota == "/monetizacao/enforcement/reservas":')
    trecho = fonte[inicio : inicio + 350]

    assert "obter_reservas_enforcement_monetizacao" in trecho
    assert "reconciliar_reserva" not in trecho
    assert "concluir_enforcement" not in trecho


# 63.8738, -149.7525
