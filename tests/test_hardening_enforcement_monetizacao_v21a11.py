from __future__ import annotations

import json
import threading
from pathlib import Path

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.controle.controlador import (
    ControladorAdministrativo,
)
from services.politica_enforcement_monetizacao import (
    CONFIRMACAO_PAUSAR,
)

RECOMENDACAO_ID = (
    "shadow:monetizacao:global:geral:" "taxa_bloqueio_critica:" "considerar_pausa_publicador"
)


def test_repository_reserva_replay_atomicamente(
    tmp_path,
):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")

    resultados = []
    barreira = threading.Barrier(8)

    def reservar():
        barreira.wait()
        resultados.append(repo.reservar_enforcement_monetizacao(RECOMENDACAO_ID))

    threads = [threading.Thread(target=reservar) for _ in range(8)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    assert resultados.count(True) == 1
    assert resultados.count(False) == 7


def test_repository_conclui_e_mantem_consumido(
    tmp_path,
):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")

    assert repo.reservar_enforcement_monetizacao(RECOMENDACAO_ID) is True

    assert repo.concluir_enforcement_monetizacao(RECOMENDACAO_ID) is True

    estado = repo.obter_enforcement_monetizacao_consumido(RECOMENDACAO_ID)

    assert estado is not None
    assert estado["status"] == "concluido"
    assert estado["concluido_em"] is not None

    assert repo.reservar_enforcement_monetizacao(RECOMENDACAO_ID) is False


def test_repository_libera_reserva_apos_falha(
    tmp_path,
):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")

    assert repo.reservar_enforcement_monetizacao(RECOMENDACAO_ID) is True

    assert repo.liberar_enforcement_monetizacao(RECOMENDACAO_ID) is True

    assert repo.reservar_enforcement_monetizacao(RECOMENDACAO_ID) is True


def test_servidor_fail_closed_sem_token():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    inicio = fonte.index("            def do_POST(self) -> None:")
    trecho = fonte[inicio : inicio + 1800]

    assert '"/monetizacao/enforcement/"' in trecho
    assert "and not token_administrativo" in trecho
    assert "503" in trecho
    assert "RADAR_ADMIN_TOKEN" in trecho


def test_servidor_ainda_exige_bearer_quando_token_existe():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    inicio = fonte.index("            def do_POST(self) -> None:")
    trecho = fonte[inicio : inicio + 3000]

    assert '"Authorization"' in trecho
    assert '"Bearer "' in trecho
    assert "hmac.compare_digest" in trecho
    assert "401" in trecho


class ExecutorControlado:
    def __init__(self):
        self.pausas = 0
        self.retomadas = 0

    def executar(
        self,
        *,
        componente,
        acao,
        dispositivo=None,
    ):
        assert componente == "publicador"

        if acao == "pausar":
            self.pausas += 1
            resultado = "pausado"
        elif acao == "retomar":
            self.retomadas += 1
            resultado = "retomado"
        else:
            raise AssertionError(f"Acao inesperada: {acao}")

        return {
            "sucesso": True,
            "componente": componente,
            "acao": acao,
            "resultado": resultado,
            "dispositivo": dispositivo,
        }


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


def _controlador_real_repo(tmp_path):
    repo = ControleAdministrativoRepository(tmp_path / "admin.db")

    repo.definir_estado(
        "observabilidade_monetizacao_v1",
        json.dumps(
            _snapshot_critico(),
            ensure_ascii=False,
            sort_keys=True,
        ),
    )

    controlador = ControladorAdministrativo(
        orquestrador=object(),
        fila=object(),
        verificador_chrome=lambda: True,
        repositorio_admin=repo,
    )

    executor = ExecutorControlado()

    controlador.executar_acao_operacional = executor.executar

    return controlador, executor, repo


def test_mesma_recomendacao_nao_executa_duas_vezes(
    tmp_path,
):
    controlador, executor, repo = _controlador_real_repo(tmp_path)

    primeira = controlador.executar_enforcement_monetizacao(
        acao="pausar",
        confirmacao=CONFIRMACAO_PAUSAR,
        recomendacao_id=RECOMENDACAO_ID,
        dispositivo="teste",
    )

    segunda = controlador.executar_enforcement_monetizacao(
        acao="pausar",
        confirmacao=CONFIRMACAO_PAUSAR,
        recomendacao_id=RECOMENDACAO_ID,
        dispositivo="teste",
    )

    assert primeira["executado"] is True
    assert segunda["executado"] is False
    assert segunda["permitido"] is False
    assert segunda["decisao"]["motivo"] == "recomendacao_ja_consumida"
    assert executor.pausas == 1

    estado = repo.obter_enforcement_monetizacao_consumido(RECOMENDACAO_ID)

    assert estado is not None
    assert estado["status"] == "concluido"


def test_replay_negado_fica_auditado(
    tmp_path,
):
    controlador, _, repo = _controlador_real_repo(tmp_path)

    for _ in range(2):
        controlador.executar_enforcement_monetizacao(
            acao="pausar",
            confirmacao=CONFIRMACAO_PAUSAR,
            recomendacao_id=RECOMENDACAO_ID,
            dispositivo="teste",
        )

    auditoria = repo.listar_auditoria(limite=10)

    assert any(
        item["acao"] == ("monetizacao.enforcement." "publicador.pausar")
        and item["resultado"] == "negado_replay"
        for item in auditoria
    )


# 63.8738, -149.7525
