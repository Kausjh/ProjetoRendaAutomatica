import os
import subprocess

from services.runtime.orquestrador import OrquestradorRuntime


class ProcessoFake:
    def __init__(self, pid=4321):
        self.pid = pid
        self.returncode = None
        self.kill_chamado = False

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        self.returncode = 1
        return self.returncode

    def kill(self):
        self.kill_chamado = True
        self.returncode = -9


def test_windows_encerra_arvore_com_taskkill(monkeypatch):
    if os.name != "nt":
        return

    processo = ProcessoFake()
    chamada = {}

    class Resultado:
        returncode = 0
        stdout = "SUCCESS"
        stderr = ""

    def run_fake(args, **kwargs):
        chamada["args"] = args
        chamada["kwargs"] = kwargs
        return Resultado()

    monkeypatch.setattr(subprocess, "run", run_fake)

    OrquestradorRuntime._encerrar_processo(
        processo=processo,
        nome="pipeline",
    )

    assert chamada["args"] == [
        "taskkill",
        "/PID",
        "4321",
        "/T",
        "/F",
    ]
    assert chamada["kwargs"]["check"] is False
    assert processo.kill_chamado is False
