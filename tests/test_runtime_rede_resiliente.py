from services.runtime.orquestrador import (
    ConfiguracoesRuntime,
    OrquestradorRuntime,
)


def config(**overrides):
    base = dict(
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
    base.update(overrides)
    return ConfiguracoesRuntime(**base)


def test_configuracoes_de_rede_validas():
    c = config()
    c.validar()


def test_aguarda_internet_ate_ficar_disponivel(monkeypatch):
    o = OrquestradorRuntime(config())
    respostas = iter([False, False, True])
    chamadas = []

    monkeypatch.setattr(
        o,
        "verificar_internet",
        lambda: next(respostas),
    )
    monkeypatch.setattr(
        "services.runtime.orquestrador.time.sleep",
        lambda segundos: chamadas.append(segundos),
    )

    o.aguardar_internet_inicial()

    assert len(chamadas) == 2


def test_bot_nao_inicia_sem_telegram(monkeypatch):
    o = OrquestradorRuntime(config())

    monkeypatch.setattr(o, "verificar_telegram", lambda: False)

    o.iniciar_bot()

    assert o.processo_bot is None


def test_publicador_nao_inicia_sem_telegram(monkeypatch):
    o = OrquestradorRuntime(config())

    monkeypatch.setattr(o, "verificar_telegram", lambda: False)

    o.iniciar_publicador()

    assert o.processo_publicador is None


def test_bot_morto_nao_e_reiniciado_enquanto_telegram_offline(monkeypatch):
    o = OrquestradorRuntime(config())

    class ProcessoMorto:
        returncode = 1

        def poll(self):
            return 1

    o.processo_bot = ProcessoMorto()

    monkeypatch.setattr(o, "verificar_telegram", lambda: False)

    chamado = {"iniciar": 0}

    monkeypatch.setattr(
        o,
        "iniciar_bot",
        lambda: chamado.__setitem__(
            "iniciar",
            chamado["iniciar"] + 1,
        ),
    )

    o.garantir_bot_ativo()

    assert chamado["iniciar"] == 0


def test_pipeline_nao_inicia_sem_mercado_livre(monkeypatch):
    o = OrquestradorRuntime(config())

    monkeypatch.setattr(
        o,
        "verificar_mercado_livre",
        lambda: False,
    )

    chamado = {"popen": 0}

    monkeypatch.setattr(
        "services.runtime.orquestrador.subprocess.Popen",
        lambda *args, **kwargs: chamado.__setitem__(
            "popen",
            chamado["popen"] + 1,
        ),
    )

    codigo = o.executar_pipeline()

    assert codigo == 0
    assert chamado["popen"] == 0


def test_estado_de_conectividade_nao_repete_transicao(monkeypatch):
    o = OrquestradorRuntime(config())

    eventos = []

    monkeypatch.setattr(
        "services.runtime.orquestrador.logger.warning",
        lambda mensagem: eventos.append(("warning", mensagem)),
    )
    monkeypatch.setattr(
        "services.runtime.orquestrador.logger.info",
        lambda mensagem: eventos.append(("info", mensagem)),
    )

    o._registrar_estado_conectividade(
        "internet",
        False,
        "offline",
        "online",
    )
    o._registrar_estado_conectividade(
        "internet",
        False,
        "offline",
        "online",
    )
    o._registrar_estado_conectividade(
        "internet",
        True,
        "offline",
        "online",
    )

    assert eventos == [
        ("warning", "offline"),
        ("info", "online"),
    ]
