# 63.8738, -149.7525

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.error import URLError
from urllib.request import urlopen


HOST_CDP: Final = "127.0.0.1"
PORTA_CDP: Final = 9222
TEMPO_LIMITE_CHROME: Final = 20.0
INTERVALO_VERIFICACAO: Final = 0.5
TEMPO_LIMITE_ENCERRAMENTO: Final = 5.0

DIRETORIO_PROJETO: Final = Path(__file__).resolve().parents[2]
ARQUIVO_MAIN: Final = DIRETORIO_PROJETO / "main.py"
DIRETORIO_PERFIL_CDP: Final = DIRETORIO_PROJETO / "browser_profile_cdp"


@dataclass(slots=True)
class EstadoChrome:
    processo: subprocess.Popen[bytes] | None = None
    iniciado_pelo_launcher: bool = False


def exibir_cabecalho() -> None:
    print("=" * 60)
    print("PROJETO RENDA AUTOMÁTICA")
    print("Launcher v2.0")
    print("=" * 60)


def exibir_rodape(duracao: float) -> None:
    print(f"Tempo total do launcher: {duracao:.2f} segundo(s).")
    print("=" * 60)


def porta_esta_aberta(
    host: str = HOST_CDP,
    porta: int = PORTA_CDP,
) -> bool:
    try:
        with socket.create_connection((host, porta), timeout=1.0):
            return True
    except OSError:
        return False


def cdp_esta_disponivel() -> bool:
    endpoint = f"http://{HOST_CDP}:{PORTA_CDP}/json/version"

    try:
        with urlopen(endpoint, timeout=2.0) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))

        return bool(dados.get("webSocketDebuggerUrl"))
    except (
        OSError,
        URLError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return False


def localizar_chrome() -> Path | None:
    candidatos: list[Path] = []

    variaveis_e_caminhos = (
        (
            os.environ.get("LOCALAPPDATA"),
            ("Google", "Chrome", "Application", "chrome.exe"),
        ),
        (
            os.environ.get("PROGRAMFILES"),
            ("Google", "Chrome", "Application", "chrome.exe"),
        ),
        (
            os.environ.get("PROGRAMFILES(X86)"),
            ("Google", "Chrome", "Application", "chrome.exe"),
        ),
    )

    for raiz, partes in variaveis_e_caminhos:
        if raiz:
            candidatos.append(Path(raiz).joinpath(*partes))

    chrome_no_path = shutil.which("chrome")

    if chrome_no_path:
        candidatos.append(Path(chrome_no_path))

    for candidato in candidatos:
        if candidato.is_file():
            return candidato

    return None


def validar_estrutura_projeto() -> None:
    if not ARQUIVO_MAIN.is_file():
        raise FileNotFoundError(
            f"O arquivo main.py não foi encontrado em: {ARQUIVO_MAIN}"
        )

    DIRETORIO_PERFIL_CDP.mkdir(parents=True, exist_ok=True)


def iniciar_chrome(executavel_chrome: Path) -> subprocess.Popen[bytes]:
    argumentos = [
        str(executavel_chrome),
        f"--remote-debugging-port={PORTA_CDP}",
        f"--user-data-dir={DIRETORIO_PERFIL_CDP}",
        "--no-first-run",
        "--no-default-browser-check",
        "about:blank",
    ]

    return subprocess.Popen(
        argumentos,
        cwd=DIRETORIO_PROJETO,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def aguardar_cdp(processo_chrome: subprocess.Popen[bytes]) -> None:
    inicio = time.monotonic()

    while time.monotonic() - inicio < TEMPO_LIMITE_CHROME:
        if processo_chrome.poll() is not None:
            raise RuntimeError(
                "O Chrome foi encerrado antes de disponibilizar "
                "a porta de depuração remota."
            )

        if cdp_esta_disponivel():
            return

        time.sleep(INTERVALO_VERIFICACAO)

    raise TimeoutError(
        "O Chrome não disponibilizou o CDP na porta "
        f"{PORTA_CDP} dentro de {TEMPO_LIMITE_CHROME:.0f} segundos."
    )


def preparar_chrome() -> EstadoChrome:
    if cdp_esta_disponivel():
        print(
            "[OK] Chrome com CDP já está disponível "
            f"na porta {PORTA_CDP}."
        )
        return EstadoChrome()

    if porta_esta_aberta():
        raise RuntimeError(
            f"A porta {PORTA_CDP} está ocupada, mas não responde "
            "como um endpoint CDP do Chrome."
        )

    executavel_chrome = localizar_chrome()

    if executavel_chrome is None:
        raise FileNotFoundError(
            "O Google Chrome não foi encontrado nos caminhos padrão "
            "do Windows."
        )

    print(f"[OK] Chrome localizado: {executavel_chrome}")
    print(
        "[...] Iniciando Chrome com depuração remota "
        f"na porta {PORTA_CDP}..."
    )

    processo = iniciar_chrome(executavel_chrome)
    estado = EstadoChrome(
        processo=processo,
        iniciado_pelo_launcher=True,
    )

    aguardar_cdp(processo)

    print("[OK] Chrome iniciado e CDP disponível.")
    return estado


def executar_projeto() -> int:
    resultado = subprocess.run(
        [sys.executable, str(ARQUIVO_MAIN)],
        cwd=DIRETORIO_PROJETO,
        check=False,
    )

    return resultado.returncode


def encerrar_chrome_iniciado(estado: EstadoChrome) -> None:
    processo = estado.processo

    if not estado.iniciado_pelo_launcher or processo is None:
        return

    if processo.poll() is not None:
        return

    print("[...] Encerrando o Chrome iniciado pelo launcher.")

    processo.terminate()

    try:
        processo.wait(timeout=TEMPO_LIMITE_ENCERRAMENTO)
    except subprocess.TimeoutExpired:
        processo.kill()
        processo.wait(timeout=TEMPO_LIMITE_ENCERRAMENTO)

    print("[OK] Chrome encerrado.")


def main() -> int:
    exibir_cabecalho()

    inicio_execucao = time.monotonic()
    estado_chrome = EstadoChrome()

    try:
        validar_estrutura_projeto()
        print("[OK] Estrutura do projeto validada.")

        estado_chrome = preparar_chrome()

        print("[...] Iniciando o ProjetoRendaAutomatica.")
        print("-" * 60)

        codigo_saida = executar_projeto()

        print("-" * 60)

        if codigo_saida == 0:
            print("[OK] Projeto finalizado com sucesso.")
        else:
            print(
                "[ERRO] O projeto terminou com o código "
                f"{codigo_saida}."
            )

        return codigo_saida

    except KeyboardInterrupt:
        print("\n[AVISO] Execução interrompida pelo usuário.")
        return 130

    except Exception as erro:
        print(f"\n[ERRO] {erro}")
        return 1

    finally:
        encerrar_chrome_iniciado(estado_chrome)

        duracao = time.monotonic() - inicio_execucao
        exibir_rodape(duracao)


if __name__ == "__main__":
    raise SystemExit(main())