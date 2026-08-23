import services.launcher.chrome_launcher as launcher


class ProcessoFake:
    def __init__(self) -> None:
        self.terminate_chamado = 0
        self.kill_chamado = 0
        self.wait_chamado = 0

    def poll(self):
        return None

    def terminate(self):
        self.terminate_chamado += 1

    def kill(self):
        self.kill_chamado += 1

    def wait(self, timeout=None):
        self.wait_chamado += 1
        return 0


def test_flag_runtime_mantem_chrome_ativo(monkeypatch):
    monkeypatch.setenv("RADAR_MANTER_CHROME_ATIVO", "1")

    assert launcher.manter_chrome_ativo_entre_ciclos() is True


def test_sem_flag_launcher_pode_encerrar_chrome(monkeypatch):
    monkeypatch.delenv("RADAR_MANTER_CHROME_ATIVO", raising=False)

    assert launcher.manter_chrome_ativo_entre_ciclos() is False


def test_launcher_nao_fecha_chrome_durante_runtime(monkeypatch):
    monkeypatch.setenv("RADAR_MANTER_CHROME_ATIVO", "1")

    processo = ProcessoFake()
    estado = launcher.EstadoChrome(
        processo=processo,
        iniciado_pelo_launcher=True,
    )

    launcher.encerrar_chrome_iniciado(estado)

    assert processo.terminate_chamado == 0
    assert processo.kill_chamado == 0
    assert processo.wait_chamado == 0


def test_launcher_fecha_chrome_fora_do_runtime(monkeypatch):
    monkeypatch.delenv("RADAR_MANTER_CHROME_ATIVO", raising=False)

    processo = ProcessoFake()
    estado = launcher.EstadoChrome(
        processo=processo,
        iniciado_pelo_launcher=True,
    )

    launcher.encerrar_chrome_iniciado(estado)

    assert processo.terminate_chamado == 1
    assert processo.wait_chamado == 1
