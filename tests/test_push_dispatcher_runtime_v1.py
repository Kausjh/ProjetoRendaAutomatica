from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import services.runtime.orquestrador as runtime_module
from models.push_dispatcher import ResultadoEnvioPush, ResultadoRecibosPush
from repositories.push_delivery_repository import PushDeliveryRepository
from services.push_dispatcher_runtime_worker import PushDispatcherRuntimeWorker
from services.runtime.orquestrador import ConfiguracoesRuntime, OrquestradorRuntime

_PUSH_ENV = (
    "RUNTIME_PUSH_DISPATCHER_ATIVO",
    "RUNTIME_PUSH_DISPATCHER_INTERVALO_SEGUNDOS",
    "RUNTIME_PUSH_DISPATCHER_ATRASO_REINICIO_SEGUNDOS",
    "RUNTIME_PUSH_DISPATCHER_RETRY_SEGUNDOS",
    "RUNTIME_PUSH_RECEIPT_MIN_AGE_SEGUNDOS",
    "RUNTIME_PUSH_MAX_ENVIOS_POR_CICLO",
)


class DispatcherFake:
    def __init__(self, statuses: list[str]) -> None:
        self.statuses = list(statuses)
        self.receipt_cutoffs: list[str | None] = []
        self.envio_calls = 0

    def processar_recibos_pendentes(
        self,
        *,
        criado_ate: str | None = None,
    ) -> ResultadoRecibosPush:
        self.receipt_cutoffs.append(criado_ate)
        return ResultadoRecibosPush(
            status="sem_recibos",
            consultados=0,
            recebidos=0,
        )

    def processar_proximo_envio(self) -> ResultadoEnvioPush:
        self.envio_calls += 1
        status = self.statuses.pop(0) if self.statuses else "sem_item"
        return ResultadoEnvioPush(
            status=status,
            outbox_id=None if status == "sem_item" else "outbox_teste",
        )


def test_config_runtime_push_e_fail_closed_por_padrao(monkeypatch):
    monkeypatch.setattr(runtime_module, "load_dotenv", lambda *args, **kwargs: False)
    for nome in _PUSH_ENV:
        monkeypatch.delenv(nome, raising=False)

    config = ConfiguracoesRuntime.carregar()

    assert config.push_dispatcher_ativo is False
    assert config.push_dispatcher_intervalo_segundos == 2.0
    assert config.push_dispatcher_atraso_reinicio_segundos == 10.0
    assert config.push_dispatcher_retry_segundos == 300
    assert config.push_dispatcher_receipt_min_age_segundos == 900
    assert config.push_dispatcher_max_envios_por_ciclo == 10


def test_worker_aplica_idade_minima_e_drena_burst():
    dispatcher = DispatcherFake(["aguardando_receipts", "aguardando_receipts", "sem_item"])
    worker = PushDispatcherRuntimeWorker(
        dispatcher=dispatcher,  # type: ignore[arg-type]
        intervalo_segundos=1,
        receipt_min_age_segundos=900,
        max_envios_por_ciclo=10,
    )

    antes = datetime.now(UTC) - timedelta(seconds=902)
    resultado = worker.executar_ciclo()
    depois = datetime.now(UTC) - timedelta(seconds=898)

    assert resultado.recibos_status == "sem_recibos"
    assert resultado.envios_processados == 2
    assert resultado.ultimo_envio_status == "sem_item"
    assert dispatcher.envio_calls == 3

    corte = datetime.fromisoformat(dispatcher.receipt_cutoffs[0] or "")
    assert antes <= corte <= depois


def test_worker_para_burst_quando_provider_pede_retry():
    dispatcher = DispatcherFake(["retry_provider", "aguardando_receipts", "sem_item"])
    worker = PushDispatcherRuntimeWorker(
        dispatcher=dispatcher,  # type: ignore[arg-type]
        intervalo_segundos=1,
        receipt_min_age_segundos=0,
        max_envios_por_ciclo=10,
    )

    resultado = worker.executar_ciclo()

    assert resultado.envios_processados == 1
    assert resultado.ultimo_envio_status == "retry_provider"
    assert dispatcher.envio_calls == 1


def test_supervisor_nao_inicia_push_quando_desativado(monkeypatch):
    orquestrador = object.__new__(OrquestradorRuntime)
    orquestrador.configuracoes = ConfiguracoesRuntime(
        push_dispatcher_ativo=False,
    )
    orquestrador.processo_push_dispatcher = None
    orquestrador._encerrando = False

    chamado = False

    def popen_proibido(*args, **kwargs):
        nonlocal chamado
        chamado = True
        raise AssertionError("Popen nao deveria ser chamado.")

    monkeypatch.setattr(runtime_module.subprocess, "Popen", popen_proibido)

    orquestrador.iniciar_push_dispatcher()

    assert chamado is False
    assert orquestrador.processo_push_dispatcher is None


def test_supervisor_inicia_processo_dedicado_quando_ativo(monkeypatch):
    orquestrador = object.__new__(OrquestradorRuntime)
    orquestrador.configuracoes = ConfiguracoesRuntime(
        push_dispatcher_ativo=True,
        push_dispatcher_atraso_reinicio_segundos=0,
    )
    orquestrador.processo_push_dispatcher = None
    orquestrador._encerrando = False

    chamadas: list[tuple[object, object]] = []
    processo = SimpleNamespace(pid=321, poll=lambda: None)

    def fake_popen(args, *, cwd):
        chamadas.append((args, cwd))
        return processo

    monkeypatch.setattr(runtime_module.subprocess, "Popen", fake_popen)

    orquestrador.iniciar_push_dispatcher()

    assert orquestrador.processo_push_dispatcher is processo
    assert len(chamadas) == 1
    args, cwd = chamadas[0]
    assert Path(args[1]).name == "push_dispatcher_runtime.py"
    assert cwd == runtime_module.DIRETORIO_PROJETO


def test_repository_filtra_receipts_por_idade(tmp_path: Path):
    banco = tmp_path / "runtime_push.sqlite3"

    with sqlite3.connect(banco) as conexao:
        conexao.executescript(
            "PRAGMA foreign_keys = ON;"
            "CREATE TABLE personalized_notification_outbox (id TEXT PRIMARY KEY);"
            "CREATE TABLE dispositivos_usuario (id TEXT PRIMARY KEY);"
            "INSERT INTO personalized_notification_outbox(id) VALUES ('outbox_1');"
            "INSERT INTO dispositivos_usuario(id) VALUES ('dev_1');"
        )

    repository = PushDeliveryRepository(banco)

    agora = datetime.now(UTC)
    antigo = (agora - timedelta(minutes=20)).isoformat()
    novo = (agora - timedelta(minutes=2)).isoformat()
    corte = (agora - timedelta(minutes=15)).isoformat()

    insert_sql = (
        "INSERT INTO push_delivery_attempts ("
        "id, outbox_id, dispositivo_id, outbox_tentativa, "
        "ticket_id, ticket_status, receipt_status, provider_error_code, "
        "ultimo_erro, criado_em, atualizado_em"
        ") VALUES (?, 'outbox_1', 'dev_1', 1, ?, 'ok', NULL, NULL, NULL, ?, ?)"
    )

    with sqlite3.connect(banco) as conexao:
        conexao.executemany(
            insert_sql,
            [
                ("attempt_old", "ticket_old", antigo, antigo),
                ("attempt_new", "ticket_new", novo, novo),
            ],
        )

    pendentes = repository.listar_aguardando_recibo(criado_ate=corte)

    assert [item.ticket_id for item in pendentes] == ["ticket_old"]


def test_contrato_e_documentacao_mantem_runtime_desligado_por_padrao():
    contrato = Path("contracts/push_dispatcher_runtime_v1.json").read_text(encoding="utf-8")
    doc = Path("docs/37-push-dispatcher-runtime-v1.md").read_text(encoding="utf-8")
    env = Path(".env.example").read_text(encoding="utf-8")

    assert '"default": false' in contrato
    assert '"real_push_during_tests": false' in contrato
    assert "RUNTIME_PUSH_DISPATCHER_ATIVO=false" in env
    assert "nao envia push real" in doc
    assert "nao faz chamadas externas nos testes" in doc
