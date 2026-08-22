from services.runtime.orquestrador import (
    CODIGO_SAIDA_REDE_INDISPONIVEL,
    ConfiguracoesRuntime,
    OrquestradorRuntime,
)


def config(**overrides):
    valores = dict(
        intervalo_minutos=30.0,
        executar_ao_iniciar=True,
        reiniciar_bot=True,
        intervalo_monitoramento_segundos=0.01,
        atraso_reinicio_bot_segundos=0.0,
        aguardar_internet_ao_iniciar=True,
        intervalo_verificacao_rede_segundos=0.01,
        timeout_verificacao_rede_segundos=0.01,
        porta_trava=48731,
    )
    valores.update(overrides)
    return ConfiguracoesRuntime(**valores)


class ProcessoFake:
    def __init__(self, pid=1234):
        self.pid = pid
        self.returncode = None
        self.terminado = False
        self.kill_chamado = False

    def poll(self):
        if self.terminado:
            return self.returncode if self.returncode is not None else -15
        return None

    def terminate(self):
        self.terminado = True
        self.returncode = -15

    def wait(self, timeout=None):
        if self.returncode is None:
            self.returncode = 0
        return self.returncode

    def kill(self):
        self.kill_chamado = True
        self.terminado = True
        self.returncode = -9


class ResultadoTaskkillFake:
    returncode = 0
    stdout = "SUCCESS"
    stderr = ""


def simular_taskkill_com_sucesso(monkeypatch):
    """Evita chamar taskkill de verdade durante testes unitários."""

    def run_fake(args, **kwargs):
        return ResultadoTaskkillFake()

    monkeypatch.setattr(
        "services.runtime.orquestrador.subprocess.run",
        run_fake,
    )


def test_suspende_bot_e_publicador_quando_telegram_cai(monkeypatch):
    o = OrquestradorRuntime(config())
    bot = ProcessoFake(pid=1111)
    publicador = ProcessoFake(pid=2222)
    o.processo_bot = bot
    o.processo_publicador = publicador

    simular_taskkill_com_sucesso(monkeypatch)

    o.suspender_servicos_telegram()

    assert o.processo_bot is None
    assert o.processo_publicador is None


def test_pipeline_interrompido_quando_ml_cai(monkeypatch):
    o = OrquestradorRuntime(config())
    pipeline = ProcessoFake(pid=3333)

    monkeypatch.setattr(
        "services.runtime.orquestrador.subprocess.Popen",
        lambda *args, **kwargs: pipeline,
    )

    simular_taskkill_com_sucesso(monkeypatch)

    respostas_ml = iter([True, False])

    monkeypatch.setattr(
        o,
        "verificar_mercado_livre",
        lambda: next(respostas_ml),
    )
    monkeypatch.setattr(o, "verificar_telegram", lambda: True)
    monkeypatch.setattr(o, "garantir_bot_ativo", lambda: None)
    monkeypatch.setattr(o, "garantir_publicador_ativo", lambda: None)
    monkeypatch.setattr(o, "suspender_servicos_telegram", lambda: None)
    monkeypatch.setattr(o, "aguardar_rede_restabelecer", lambda: None)
    monkeypatch.setattr(
        "services.runtime.orquestrador.time.sleep",
        lambda segundos: None,
    )

    codigo = o.executar_pipeline()

    assert codigo == CODIGO_SAIDA_REDE_INDISPONIVEL


def test_aguarda_rede_e_reinicia_servicos(monkeypatch):
    o = OrquestradorRuntime(config())

    internet = iter([False, True])
    telegram = iter([False, True])
    mercado = iter([False, True])

    monkeypatch.setattr(
        o,
        "verificar_internet",
        lambda: next(internet),
    )
    monkeypatch.setattr(
        o,
        "verificar_telegram",
        lambda: next(telegram),
    )
    monkeypatch.setattr(
        o,
        "verificar_mercado_livre",
        lambda: next(mercado),
    )
    monkeypatch.setattr(
        "services.runtime.orquestrador.time.sleep",
        lambda segundos: None,
    )

    chamados = {
        "bot": 0,
        "publicador": 0,
    }

    monkeypatch.setattr(
        o,
        "iniciar_bot",
        lambda: chamados.__setitem__(
            "bot",
            chamados["bot"] + 1,
        ),
    )
    monkeypatch.setattr(
        o,
        "iniciar_publicador",
        lambda: chamados.__setitem__(
            "publicador",
            chamados["publicador"] + 1,
        ),
    )

    o.aguardar_rede_restabelecer()

    assert chamados == {
        "bot": 1,
        "publicador": 1,
    }


def test_sem_ml_antes_do_ciclo_mantem_compatibilidade(monkeypatch):
    o = OrquestradorRuntime(config())

    monkeypatch.setattr(
        o,
        "verificar_mercado_livre",
        lambda: False,
    )

    assert o.executar_pipeline() == 0
