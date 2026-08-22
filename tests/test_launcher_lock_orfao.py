import json
import time

import services.launcher.chrome_launcher as launcher


def configurar_trava_temporaria(monkeypatch, tmp_path, dados):
    arquivo = tmp_path / "execucao_em_andamento.lock"
    arquivo.write_text(json.dumps(dados), encoding="utf-8")
    monkeypatch.setattr(launcher, "ARQUIVO_TRAVA", arquivo)
    return arquivo


def test_pid_morto_torna_trava_abandonada(monkeypatch, tmp_path):
    configurar_trava_temporaria(
        monkeypatch,
        tmp_path,
        {"pid": 18924, "iniciado_em": time.time()},
    )

    monkeypatch.setattr(launcher, "processo_existe", lambda pid: False)

    motivo = launcher.motivo_trava_abandonada()

    assert motivo is not None
    assert "não existe mais" in motivo
    assert launcher.trava_esta_abandonada() is True


def test_pid_vivo_do_launcher_mantem_trava(monkeypatch, tmp_path):
    configurar_trava_temporaria(
        monkeypatch,
        tmp_path,
        {"pid": 12345, "iniciado_em": time.time()},
    )

    monkeypatch.setattr(launcher, "processo_existe", lambda pid: True)
    monkeypatch.setattr(
        launcher,
        "obter_linha_comando_processo",
        lambda pid: (
            r'"C:\Python313\python.exe" '
            r"C:\Projetos\ProjetoRendaAutomatica\services\launcher"
            r"\chrome_launcher.py"
        ),
    )

    assert launcher.motivo_trava_abandonada() is None
    assert launcher.trava_esta_abandonada() is False


def test_pid_reutilizado_por_outro_programa_e_trava_orfa(
    monkeypatch,
    tmp_path,
):
    configurar_trava_temporaria(
        monkeypatch,
        tmp_path,
        {"pid": 12345, "iniciado_em": time.time()},
    )

    monkeypatch.setattr(launcher, "processo_existe", lambda pid: True)
    monkeypatch.setattr(
        launcher,
        "obter_linha_comando_processo",
        lambda pid: r'"C:\Windows\System32\notepad.exe"',
    )

    motivo = launcher.motivo_trava_abandonada()

    assert motivo is not None
    assert "reutilizado" in motivo


def test_lock_corrompido_e_recuperavel(monkeypatch, tmp_path):
    arquivo = tmp_path / "execucao_em_andamento.lock"
    arquivo.write_text("{isso nao e json", encoding="utf-8")
    monkeypatch.setattr(launcher, "ARQUIVO_TRAVA", arquivo)

    motivo = launcher.motivo_trava_abandonada()

    assert motivo is not None
    assert "corrompido" in motivo


def test_lock_antigo_nao_e_removido_se_processo_real_esta_vivo(
    monkeypatch,
    tmp_path,
):
    configurar_trava_temporaria(
        monkeypatch,
        tmp_path,
        {
            "pid": 54321,
            "iniciado_em": time.time() - launcher.IDADE_MAXIMA_TRAVA_SEGUNDOS - 3600,
        },
    )

    monkeypatch.setattr(launcher, "processo_existe", lambda pid: True)
    monkeypatch.setattr(
        launcher,
        "obter_linha_comando_processo",
        lambda pid: "python.exe launcher.py",
    )

    assert launcher.motivo_trava_abandonada() is None


def test_adquirir_trava_remove_pid_morto_e_cria_nova(
    monkeypatch,
    tmp_path,
):
    arquivo = configurar_trava_temporaria(
        monkeypatch,
        tmp_path,
        {"pid": 18924, "iniciado_em": time.time()},
    )

    monkeypatch.setattr(launcher, "processo_existe", lambda pid: False)

    assert launcher.adquirir_trava() is True

    dados_novos = json.loads(arquivo.read_text(encoding="utf-8"))

    assert dados_novos["pid"] == launcher.os.getpid()
    assert dados_novos["pid"] != 18924
