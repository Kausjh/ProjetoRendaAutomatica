# 63.8738, -149.7525

from __future__ import annotations

import ctypes
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

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

HOST_CDP: Final = "127.0.0.1"
PORTA_CDP: Final = 9222
TEMPO_LIMITE_CHROME: Final = 20.0
INTERVALO_VERIFICACAO: Final = 0.5
TEMPO_LIMITE_ENCERRAMENTO: Final = 5.0
ENV_MANTER_CHROME_ATIVO: Final = "RADAR_MANTER_CHROME_ATIVO"
TEMPO_LIMITE_TESTE_CDP_MS: Final = 5_000
INTERVALO_ESPERA_PORTA_CDP: Final = 0.25

DIRETORIO_PROJETO: Final = Path(__file__).resolve().parents[2]
ARQUIVO_MAIN: Final = DIRETORIO_PROJETO / "main.py"
DIRETORIO_PERFIL_CDP: Final = DIRETORIO_PROJETO / "browser_profile_cdp"

ARQUIVO_TRAVA: Final = DIRETORIO_PROJETO / "execucao_em_andamento.lock"

# Depois desse tempo, uma trava é considerada abandonada (processo
# morto sem limpar o arquivo) e pode ser assumida por outra execução.
IDADE_MAXIMA_TRAVA_SEGUNDOS: Final = 45 * 60

CODIGO_SAIDA_JA_EM_EXECUCAO: Final = 75


@dataclass(slots=True)
class EstadoChrome:
    processo: subprocess.Popen[bytes] | None = None
    iniciado_pelo_launcher: bool = False


def exibir_cabecalho() -> None:
    print("=" * 60)
    print("PROJETO RENDA AUTOMÁTICA")
    print("Launcher v2.2")
    print("=" * 60)


def exibir_rodape(duracao: float) -> None:
    print(f"Tempo total do launcher: {duracao:.2f} segundo(s).")
    print("=" * 60)


def ler_trava() -> dict[str, object] | None:
    try:
        conteudo = ARQUIVO_TRAVA.read_text(encoding="utf-8")
        dados = json.loads(conteudo)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(dados, dict):
        return None

    return dados


def processo_existe(pid: int) -> bool:
    """Verifica se um PID ainda existe sem encerrar ou alterar o processo."""

    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False

    if os.name == "nt":
        acesso = 0x1000  # PROCESS_QUERY_LIMITED_INFORMATION

        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            abrir_processo = kernel32.OpenProcess
            abrir_processo.argtypes = [
                ctypes.c_ulong,
                ctypes.c_int,
                ctypes.c_ulong,
            ]
            abrir_processo.restype = ctypes.c_void_p

            fechar_handle = kernel32.CloseHandle
            fechar_handle.argtypes = [ctypes.c_void_p]
            fechar_handle.restype = ctypes.c_int

            handle = abrir_processo(acesso, 0, pid)

            if handle:
                fechar_handle(handle)
                return True

            return ctypes.get_last_error() == 5

        except (AttributeError, OSError):
            pass

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False

    return True


def obter_linha_comando_processo(pid: int) -> str | None:
    """Obtém a linha de comando do PID no Windows."""

    if os.name != "nt":
        return None

    comando = (
        "$p = Get-CimInstance Win32_Process "
        f'-Filter "ProcessId = {pid}" -ErrorAction SilentlyContinue; '
        "if ($null -ne $p) { $p.CommandLine }"
    )

    try:
        resultado = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                comando,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if resultado.returncode != 0:
        return None

    linha = resultado.stdout.strip()

    return linha or None


def linha_comando_parece_ser_do_projeto(linha_comando: str) -> bool:
    """Evita aceitar trava cujo PID já foi reutilizado por outro programa."""

    texto = linha_comando.casefold().replace("\\", "/")

    nomes_validos = (
        "chrome_launcher.py",
        "launcher.py",
        "main.py",
    )

    return any(nome in texto for nome in nomes_validos)


def processo_da_trava_esta_ativo(dados: dict[str, object]) -> bool:
    pid = dados.get("pid")

    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return False

    if not processo_existe(pid):
        return False

    linha_comando = obter_linha_comando_processo(pid)

    if linha_comando is None:
        # Conservador: PID existe, mas não conseguimos inspecioná-lo.
        return True

    return linha_comando_parece_ser_do_projeto(linha_comando)


def motivo_trava_abandonada() -> str | None:
    """Retorna o motivo se a trava for órfã; None se estiver realmente ativa."""

    dados = ler_trava()

    if dados is None:
        return "arquivo de trava ilegível ou corrompido"

    pid = dados.get("pid")

    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return "PID ausente ou inválido no arquivo de trava"

    if not processo_existe(pid):
        return f"o processo {pid} não existe mais"

    linha_comando = obter_linha_comando_processo(pid)

    if linha_comando is not None and not linha_comando_parece_ser_do_projeto(linha_comando):
        return f"o PID {pid} foi reutilizado por outro processo " "que não pertence ao launcher"

    iniciado_em = dados.get("iniciado_em")

    if not isinstance(iniciado_em, (int, float)) or isinstance(iniciado_em, bool):
        return None

    idade = max(0.0, time.time() - float(iniciado_em))

    if idade > IDADE_MAXIMA_TRAVA_SEGUNDOS:
        idade_minutos = idade / 60

        print(
            "[AVISO] A trava ativa tem aproximadamente "
            f"{idade_minutos:.0f} minutos, mas o processo {pid} "
            "ainda existe. A execução continuará protegida."
        )

    return None


def trava_esta_abandonada() -> bool:
    """Indica se a trava existente pode ser descartada com segurança."""

    return motivo_trava_abandonada() is not None


def adquirir_trava() -> bool:
    """Cria a trava. False significa que já há uma execução real ativa."""

    for tentativa in range(2):
        try:
            descritor = os.open(
                ARQUIVO_TRAVA,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError:
            motivo = motivo_trava_abandonada()

            if tentativa == 0 and motivo is not None:
                dados = ler_trava() or {}
                pid = dados.get("pid", "desconhecido")

                print(
                    "[AVISO] Trava órfã detectada "
                    f"(PID {pid}): {motivo}. "
                    "Removendo automaticamente e retomando a execução."
                )

                liberar_trava()
                continue

            return False
        except OSError as erro:
            print("[AVISO] Não foi possível criar a trava de execução: " f"{erro}")
            return True

        conteudo = json.dumps(
            {
                "pid": os.getpid(),
                "iniciado_em": time.time(),
            }
        )

        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            arquivo.write(conteudo)

        return True

    return False


def liberar_trava() -> None:
    try:
        ARQUIVO_TRAVA.unlink(missing_ok=True)
    except OSError as erro:
        print(f"[AVISO] Não foi possível remover a trava de execução: {erro}")


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


def cdp_esta_funcional() -> bool:
    """Confirma que o Playwright consegue usar a sessão CDP de verdade."""

    if not cdp_esta_disponivel():
        return False

    endpoint = f"http://{HOST_CDP}:{PORTA_CDP}"

    try:
        with sync_playwright() as playwright:
            navegador = playwright.chromium.connect_over_cdp(
                endpoint,
                timeout=TEMPO_LIMITE_TESTE_CDP_MS,
            )
            _ = navegador.contexts
        return True
    except (PlaywrightError, OSError):
        return False


def localizar_pids_chrome_automacao() -> list[int]:
    """Localiza somente o Chrome iniciado com porta/perfil deste projeto."""

    if os.name != "nt":
        return []

    comando = (
        "$processos = Get-CimInstance Win32_Process "
        "-Filter \"Name = 'chrome.exe'\" -ErrorAction SilentlyContinue; "
        "$processos | Where-Object { "
        "$cmd = $_.CommandLine; "
        "$null -ne $cmd -and "
        f"$cmd -match '--remote-debugging-port={PORTA_CDP}' -and "
        "$cmd -match 'browser_profile_cdp' "
        "} | Select-Object -ExpandProperty ProcessId"
    )

    try:
        resultado = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                comando,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, subprocess.TimeoutExpired):
        return []

    if resultado.returncode != 0:
        return []

    pids: list[int] = []

    for linha in resultado.stdout.splitlines():
        try:
            pid = int(linha.strip())
        except ValueError:
            continue

        if pid > 0 and pid not in pids:
            pids.append(pid)

    return pids


def aguardar_porta_cdp_liberar() -> bool:
    inicio = time.monotonic()

    while time.monotonic() - inicio < TEMPO_LIMITE_ENCERRAMENTO:
        if not porta_esta_aberta():
            return True

        time.sleep(INTERVALO_ESPERA_PORTA_CDP)

    return not porta_esta_aberta()


def encerrar_chrome_automacao_travado() -> None:
    """Encerra somente a árvore do Chrome dedicada ao projeto."""

    pids = localizar_pids_chrome_automacao()

    if not pids:
        raise RuntimeError(
            "O CDP está travado, mas não foi possível identificar "
            "com segurança o Chrome de automação."
        )

    print(
        "[AVISO] Chrome/CDP de automação travado. "
        f"Reiniciando {len(pids)} processo(s) raiz identificado(s)."
    )

    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue

    if not aguardar_porta_cdp_liberar():
        raise RuntimeError(
            "O Chrome de automação foi encerrado, mas a porta " f"{PORTA_CDP} continuou ocupada."
        )

    print("[OK] Chrome/CDP travado encerrado. A sessão será recriada.")


def manter_chrome_ativo_entre_ciclos() -> bool:
    valor = os.environ.get(ENV_MANTER_CHROME_ATIVO, "").strip().lower()
    return valor in {"1", "true", "yes", "sim", "on"}


def encerrar_chrome_automacao() -> None:
    """Encerra, com segurança, apenas o Chrome dedicado ao projeto."""

    pids = localizar_pids_chrome_automacao()

    if not pids:
        return

    print(
        "[...] Encerrando Chrome de automação persistente "
        f"({len(pids)} processo(s) raiz identificado(s))."
    )

    for pid in pids:
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue

    if not aguardar_porta_cdp_liberar():
        raise RuntimeError(
            "O Chrome de automação foi encerrado, mas a porta " f"{PORTA_CDP} continuou ocupada."
        )

    print("[OK] Chrome de automação persistente encerrado.")


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
        raise FileNotFoundError(f"O arquivo main.py não foi encontrado em: {ARQUIVO_MAIN}")

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
                "O Chrome foi encerrado antes de disponibilizar " "a porta de depuração remota."
            )

        if cdp_esta_funcional():
            return

        time.sleep(INTERVALO_VERIFICACAO)

    raise TimeoutError(
        "O Chrome não disponibilizou uma sessão CDP funcional na porta "
        f"{PORTA_CDP} dentro de {TEMPO_LIMITE_CHROME:.0f} segundos."
    )


def preparar_chrome() -> EstadoChrome:
    if cdp_esta_disponivel():
        if cdp_esta_funcional():
            print("[OK] Chrome com CDP funcional já está disponível " f"na porta {PORTA_CDP}.")
            return EstadoChrome()

        print(
            "[AVISO] A porta 9222 responde como CDP, mas o Playwright "
            "não consegue estabelecer uma sessão funcional."
        )
        encerrar_chrome_automacao_travado()

    elif porta_esta_aberta():
        if not localizar_pids_chrome_automacao():
            raise RuntimeError(
                f"A porta {PORTA_CDP} está ocupada por um processo "
                "que não foi identificado como o Chrome de automação."
            )

        print(
            "[AVISO] A porta 9222 está ocupada pelo Chrome de automação, "
            "mas o endpoint CDP não responde corretamente."
        )
        encerrar_chrome_automacao_travado()

    executavel_chrome = localizar_chrome()

    if executavel_chrome is None:
        raise FileNotFoundError(
            "O Google Chrome não foi encontrado nos caminhos padrão " "do Windows."
        )

    print(f"[OK] Chrome localizado: {executavel_chrome}")
    print("[...] Iniciando Chrome com depuração remota " f"na porta {PORTA_CDP}...")

    processo = iniciar_chrome(executavel_chrome)
    estado = EstadoChrome(
        processo=processo,
        iniciado_pelo_launcher=True,
    )

    aguardar_cdp(processo)

    print("[OK] Chrome iniciado e CDP funcional.")
    return estado


def executar_projeto() -> int:
    resultado = subprocess.run(
        [sys.executable, str(ARQUIVO_MAIN)],
        cwd=DIRETORIO_PROJETO,
        check=False,
    )

    return resultado.returncode


def encerrar_chrome_iniciado(estado: EstadoChrome) -> None:
    if manter_chrome_ativo_entre_ciclos():
        if estado.iniciado_pelo_launcher:
            print("[OK] Chrome mantido ativo para o runtime, publicador e próximos ciclos.")
        return

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

    if not adquirir_trava():
        dados = ler_trava() or {}
        pid = dados.get("pid", "desconhecido")

        print(
            "[AVISO] Já existe uma execução em andamento "
            f"(processo {pid}). Esta execução será encerrada "
            "para não disputar o navegador nem a sessão do "
            "Mercado Livre."
        )
        print("=" * 60)

        return CODIGO_SAIDA_JA_EM_EXECUCAO

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
            print("[ERRO] O projeto terminou com o código " f"{codigo_saida}.")

        return codigo_saida

    except KeyboardInterrupt:
        print("\n[AVISO] Execução interrompida pelo usuário.")
        return 130

    except Exception as erro:
        print(f"\n[ERRO] {erro}")
        return 1

    finally:
        encerrar_chrome_iniciado(estado_chrome)

        liberar_trava()

        duracao = time.monotonic() - inicio_execucao
        exibir_rodape(duracao)


if __name__ == "__main__":
    raise SystemExit(main())
