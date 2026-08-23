from pathlib import Path

import services.launcher.chrome_launcher as launcher


class ProcessoFake:
    def poll(self):
        return None


def test_preparar_chrome_reutiliza_cdp_funcional(monkeypatch):
    monkeypatch.setattr(launcher, "cdp_esta_disponivel", lambda: True)
    monkeypatch.setattr(launcher, "cdp_esta_funcional", lambda: True)

    estado = launcher.preparar_chrome()

    assert estado.processo is None
    assert estado.iniciado_pelo_launcher is False


def test_preparar_chrome_reinicia_cdp_travado(monkeypatch):
    processo = ProcessoFake()
    chamadas = {"encerrou": 0, "iniciou": 0, "aguardou": 0}

    monkeypatch.setattr(launcher, "cdp_esta_disponivel", lambda: True)
    monkeypatch.setattr(launcher, "cdp_esta_funcional", lambda: False)

    def encerrar():
        chamadas["encerrou"] += 1

    def iniciar(_executavel):
        chamadas["iniciou"] += 1
        return processo

    def aguardar(processo_recebido):
        assert processo_recebido is processo
        chamadas["aguardou"] += 1

    monkeypatch.setattr(launcher, "encerrar_chrome_automacao_travado", encerrar)
    monkeypatch.setattr(
        launcher,
        "localizar_chrome",
        lambda: Path(r"C:\Chrome\chrome.exe"),
    )
    monkeypatch.setattr(launcher, "iniciar_chrome", iniciar)
    monkeypatch.setattr(launcher, "aguardar_cdp", aguardar)

    estado = launcher.preparar_chrome()

    assert chamadas == {"encerrou": 1, "iniciou": 1, "aguardou": 1}
    assert estado.processo is processo
    assert estado.iniciado_pelo_launcher is True


def test_preparar_chrome_nao_mata_processo_desconhecido(monkeypatch):
    monkeypatch.setattr(launcher, "cdp_esta_disponivel", lambda: False)
    monkeypatch.setattr(launcher, "porta_esta_aberta", lambda: True)
    monkeypatch.setattr(launcher, "localizar_pids_chrome_automacao", lambda: [])

    try:
        launcher.preparar_chrome()
    except RuntimeError as erro:
        assert "não foi identificado como o Chrome de automação" in str(erro)
    else:
        raise AssertionError("Era esperado RuntimeError.")
