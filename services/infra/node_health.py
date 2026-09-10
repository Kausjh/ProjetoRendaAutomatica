# 63.8738, -149.7525

from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Final
from urllib.error import URLError
from urllib.request import urlopen

from models.estado_node import (
    EstadoNode,
    EstadoServicoNode,
)

DIRETORIO_PROJETO: Final = Path(__file__).resolve().parents[2]

CAMINHO_ESTADO_PADRAO: Final = DIRETORIO_PROJETO / "data" / "node" / "estado_atual.json"

CAMINHO_LOCK_PIPELINE: Final = DIRETORIO_PROJETO / "execucao_em_andamento.lock"

CDP_ENDPOINT: Final = "http://127.0.0.1:9222/json/version"

INTERVALO_AMOSTRA_CPU: Final = 0.20


@dataclass(frozen=True, slots=True)
class ProcessoNode:
    pid: int
    parent_pid: int
    nome: str
    linha_comando: str
    memoria_rss_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class MetricasSistema:
    uptime_segundos: float | None
    cpu_percentual: float | None

    memoria_total_bytes: int | None
    memoria_disponivel_bytes: int | None
    memoria_uso_percentual: float | None


class _FileTime(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime", ctypes.c_ulong),
        ("dwHighDateTime", ctypes.c_ulong),
    ]


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _filetime_para_inteiro(valor: _FileTime) -> int:
    return (int(valor.dwHighDateTime) << 32) | int(valor.dwLowDateTime)


def _amostra_cpu_windows() -> tuple[int, int, int] | None:
    try:
        kernel32 = ctypes.WinDLL(
            "kernel32",
            use_last_error=True,
        )
    except (AttributeError, OSError):
        return None

    idle = _FileTime()
    kernel = _FileTime()
    user = _FileTime()

    get_system_times = kernel32.GetSystemTimes
    get_system_times.argtypes = [
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
        ctypes.POINTER(_FileTime),
    ]
    get_system_times.restype = ctypes.c_int

    if not get_system_times(
        ctypes.byref(idle),
        ctypes.byref(kernel),
        ctypes.byref(user),
    ):
        return None

    return (
        _filetime_para_inteiro(idle),
        _filetime_para_inteiro(kernel),
        _filetime_para_inteiro(user),
    )


def _cpu_percentual_windows() -> float | None:
    primeira = _amostra_cpu_windows()

    if primeira is None:
        return None

    time.sleep(INTERVALO_AMOSTRA_CPU)

    segunda = _amostra_cpu_windows()

    if segunda is None:
        return None

    idle_delta = segunda[0] - primeira[0]
    kernel_delta = segunda[1] - primeira[1]
    user_delta = segunda[2] - primeira[2]

    total = kernel_delta + user_delta

    if total <= 0:
        return None

    uso = (total - idle_delta) / total * 100.0

    return round(
        max(
            0.0,
            min(100.0, uso),
        ),
        2,
    )


def _memoria_windows() -> tuple[
    int | None,
    int | None,
    float | None,
]:
    try:
        kernel32 = ctypes.WinDLL(
            "kernel32",
            use_last_error=True,
        )
    except (AttributeError, OSError):
        return None, None, None

    estado = _MemoryStatusEx()
    estado.dwLength = ctypes.sizeof(_MemoryStatusEx)

    global_memory_status = kernel32.GlobalMemoryStatusEx

    global_memory_status.argtypes = [ctypes.POINTER(_MemoryStatusEx)]
    global_memory_status.restype = ctypes.c_int

    if not global_memory_status(ctypes.byref(estado)):
        return None, None, None

    total = int(estado.ullTotalPhys)
    disponivel = int(estado.ullAvailPhys)

    if total <= 0:
        return total, disponivel, None

    uso = (total - disponivel) / total * 100.0

    return (
        total,
        disponivel,
        round(uso, 2),
    )


def _uptime_windows() -> float | None:
    try:
        kernel32 = ctypes.WinDLL(
            "kernel32",
            use_last_error=True,
        )
    except (AttributeError, OSError):
        return None

    get_tick_count = kernel32.GetTickCount64
    get_tick_count.restype = ctypes.c_ulonglong

    return round(
        float(get_tick_count()) / 1000.0,
        2,
    )


def _amostra_cpu_linux() -> (
    tuple[
        int,
        int,
    ]
    | None
):
    caminho = Path("/proc/stat")

    try:
        linha = caminho.read_text(
            encoding="utf-8",
        ).splitlines()[0]
    except (
        OSError,
        IndexError,
        UnicodeDecodeError,
    ):
        return None

    partes = linha.split()

    if not partes or partes[0] != "cpu":
        return None

    try:
        valores = [int(valor) for valor in partes[1:]]
    except ValueError:
        return None

    if len(valores) < 4:
        return None

    idle = valores[3]

    if len(valores) > 4:
        idle += valores[4]

    total = sum(valores)

    return idle, total


def _cpu_percentual_linux() -> float | None:
    primeira = _amostra_cpu_linux()

    if primeira is None:
        return None

    time.sleep(INTERVALO_AMOSTRA_CPU)

    segunda = _amostra_cpu_linux()

    if segunda is None:
        return None

    idle_delta = segunda[0] - primeira[0]
    total_delta = segunda[1] - primeira[1]

    if total_delta <= 0:
        return None

    uso = (total_delta - idle_delta) / total_delta * 100.0

    return round(
        max(
            0.0,
            min(100.0, uso),
        ),
        2,
    )


def _memoria_linux() -> tuple[
    int | None,
    int | None,
    float | None,
]:
    caminho = Path("/proc/meminfo")

    try:
        linhas = caminho.read_text(
            encoding="utf-8",
        ).splitlines()
    except (
        OSError,
        UnicodeDecodeError,
    ):
        return None, None, None

    valores: dict[str, int] = {}

    for linha in linhas:
        if ":" not in linha:
            continue

        chave, restante = linha.split(
            ":",
            maxsplit=1,
        )

        partes = restante.strip().split()

        if not partes:
            continue

        try:
            valores[chave] = int(partes[0]) * 1024
        except ValueError:
            continue

    total = valores.get("MemTotal")
    disponivel = valores.get("MemAvailable")

    if total is None or disponivel is None or total <= 0:
        return total, disponivel, None

    uso = (total - disponivel) / total * 100.0

    return (
        total,
        disponivel,
        round(uso, 2),
    )


def _uptime_linux() -> float | None:
    try:
        valor = (
            Path("/proc/uptime")
            .read_text(
                encoding="utf-8",
            )
            .split()[0]
        )

        return round(
            float(valor),
            2,
        )

    except (
        OSError,
        ValueError,
        IndexError,
        UnicodeDecodeError,
    ):
        return None


def _obter_metricas_sistema() -> MetricasSistema:
    sistema = platform.system().casefold()

    if sistema == "windows":
        total, disponivel, uso = _memoria_windows()

        return MetricasSistema(
            uptime_segundos=(_uptime_windows()),
            cpu_percentual=(_cpu_percentual_windows()),
            memoria_total_bytes=total,
            memoria_disponivel_bytes=(disponivel),
            memoria_uso_percentual=uso,
        )

    if sistema == "linux":
        total, disponivel, uso = _memoria_linux()

        return MetricasSistema(
            uptime_segundos=(_uptime_linux()),
            cpu_percentual=(_cpu_percentual_linux()),
            memoria_total_bytes=total,
            memoria_disponivel_bytes=(disponivel),
            memoria_uso_percentual=uso,
        )

    return MetricasSistema(
        uptime_segundos=None,
        cpu_percentual=None,
        memoria_total_bytes=None,
        memoria_disponivel_bytes=None,
        memoria_uso_percentual=None,
    )


def _listar_processos_windows() -> tuple[
    ProcessoNode,
    ...,
]:
    comando = (
        "[Console]::OutputEncoding = "
        "[System.Text.Encoding]::UTF8; "
        "Get-CimInstance Win32_Process "
        "-ErrorAction SilentlyContinue | "
        "Select-Object "
        "ProcessId,"
        "ParentProcessId,"
        "Name,"
        "WorkingSetSize,"
        "CommandLine | "
        "ConvertTo-Json -Compress"
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
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=15,
        )
    except (
        OSError,
        subprocess.TimeoutExpired,
    ):
        return ()

    if resultado.returncode != 0:
        return ()

    texto = resultado.stdout.strip()

    if not texto:
        return ()

    try:
        dados = json.loads(texto)
    except json.JSONDecodeError:
        return ()

    if isinstance(dados, dict):
        dados = [dados]

    if not isinstance(dados, list):
        return ()

    processos: list[ProcessoNode] = []

    for item in dados:
        if not isinstance(item, dict):
            continue

        try:
            pid = int(item.get("ProcessId", 0))
            parent_pid = int(
                item.get(
                    "ParentProcessId",
                    0,
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        if pid <= 0:
            continue

        memoria_bruta = item.get("WorkingSetSize")

        try:
            memoria = int(memoria_bruta) if memoria_bruta is not None else None
        except (
            TypeError,
            ValueError,
        ):
            memoria = None

        processos.append(
            ProcessoNode(
                pid=pid,
                parent_pid=parent_pid,
                nome=str(item.get("Name") or ""),
                linha_comando=str(item.get("CommandLine") or ""),
                memoria_rss_bytes=memoria,
            )
        )

    return tuple(processos)


def _listar_processos_posix() -> tuple[
    ProcessoNode,
    ...,
]:
    try:
        resultado = subprocess.run(
            [
                "ps",
                "-eo",
                "pid=,ppid=,rss=,comm=,args=",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=10,
        )
    except (
        OSError,
        subprocess.TimeoutExpired,
    ):
        return ()

    if resultado.returncode != 0:
        return ()

    processos: list[ProcessoNode] = []

    for linha in resultado.stdout.splitlines():
        partes = linha.strip().split(
            None,
            4,
        )

        if len(partes) < 4:
            continue

        try:
            pid = int(partes[0])
            parent_pid = int(partes[1])
        except ValueError:
            continue

        try:
            memoria = int(partes[2]) * 1024
        except ValueError:
            memoria = None

        nome = partes[3]

        linha_comando = partes[4] if len(partes) == 5 else nome

        processos.append(
            ProcessoNode(
                pid=pid,
                parent_pid=parent_pid,
                nome=nome,
                linha_comando=linha_comando,
                memoria_rss_bytes=memoria,
            )
        )

    return tuple(processos)


def _listar_processos() -> tuple[
    ProcessoNode,
    ...,
]:
    if os.name == "nt":
        return _listar_processos_windows()

    if os.name == "posix":
        return _listar_processos_posix()

    return ()


def _normalizar_texto_processo(
    texto: str,
) -> str:
    return texto.casefold().replace("\\", "/")


def _processo_pertence_projeto(
    processo: ProcessoNode,
    diretorio_projeto: Path,
) -> bool:
    raiz = _normalizar_texto_processo(str(diretorio_projeto.resolve()))

    comando = _normalizar_texto_processo(processo.linha_comando)

    return raiz in comando


def _buscar_pids(
    processos: tuple[
        ProcessoNode,
        ...,
    ],
    diretorio_projeto: Path,
    termo: str,
) -> tuple[int, ...]:
    termo = _normalizar_texto_processo(termo)

    encontrados = [
        processo.pid
        for processo in processos
        if (
            _processo_pertence_projeto(
                processo,
                diretorio_projeto,
            )
            and termo in _normalizar_texto_processo(processo.linha_comando)
        )
    ]

    return tuple(sorted(set(encontrados)))


def _buscar_chrome_cdp_pids(
    processos: tuple[
        ProcessoNode,
        ...,
    ],
    diretorio_projeto: Path,
) -> tuple[int, ...]:
    raiz = _normalizar_texto_processo(str(diretorio_projeto.resolve()))

    encontrados: list[int] = []

    for processo in processos:
        comando = _normalizar_texto_processo(processo.linha_comando)

        nome = processo.nome.casefold()

        if "chrome" not in nome:
            continue

        if "browser_profile_cdp" not in comando:
            continue

        if raiz not in comando:
            continue

        encontrados.append(processo.pid)

    return tuple(sorted(set(encontrados)))


def _somar_memoria_processos(
    processos: tuple[
        ProcessoNode,
        ...,
    ],
    pids: tuple[int, ...] | None = None,
) -> int | None:
    if pids is None:
        selecionados = processos
    else:
        ids = set(pids)

        selecionados = tuple(processo for processo in processos if processo.pid in ids)

    if not selecionados:
        return 0

    valores = [
        processo.memoria_rss_bytes
        for processo in selecionados
        if (processo.memoria_rss_bytes is not None and processo.memoria_rss_bytes >= 0)
    ]

    if not valores:
        return None

    return int(sum(valores))


def _cdp_esta_disponivel() -> bool:
    try:
        with urlopen(
            CDP_ENDPOINT,
            timeout=2.0,
        ) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))

        return bool(dados.get("webSocketDebuggerUrl"))

    except (
        OSError,
        URLError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return False


def _estado_pipeline(
    processos: tuple[
        ProcessoNode,
        ...,
    ],
    caminho_lock: Path,
) -> EstadoServicoNode:
    if not caminho_lock.exists():
        return EstadoServicoNode(
            nome="pipeline",
            ativo=False,
            detalhes="sem_lock",
        )

    try:
        dados = json.loads(
            caminho_lock.read_text(
                encoding="utf-8",
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
        UnicodeDecodeError,
    ):
        return EstadoServicoNode(
            nome="pipeline",
            ativo=False,
            detalhes="lock_invalido",
        )

    if not isinstance(dados, dict):
        return EstadoServicoNode(
            nome="pipeline",
            ativo=False,
            detalhes="lock_invalido",
        )

    pid = dados.get("pid")

    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        return EstadoServicoNode(
            nome="pipeline",
            ativo=False,
            detalhes="lock_sem_pid_valido",
        )

    processo = next(
        (processo for processo in processos if processo.pid == pid),
        None,
    )

    if processo is None:
        return EstadoServicoNode(
            nome="pipeline",
            ativo=False,
            pids=(pid,),
            detalhes="lock_sem_processo",
        )

    return EstadoServicoNode(
        nome="pipeline",
        ativo=True,
        pids=(pid,),
        detalhes="lock_com_processo_ativo",
        memoria_rss_bytes=(processo.memoria_rss_bytes),
    )


def _metricas_disco(
    diretorio_projeto: Path,
) -> tuple[
    int | None,
    int | None,
    float | None,
]:
    try:
        raiz = Path(diretorio_projeto.anchor or "/")

        uso = shutil.disk_usage(raiz)
    except OSError:
        return None, None, None

    if uso.total <= 0:
        return (
            int(uso.total),
            int(uso.free),
            None,
        )

    percentual = uso.used / uso.total * 100.0

    return (
        int(uso.total),
        int(uso.free),
        round(percentual, 2),
    )


def capturar_estado_node(
    node_id: str,
    diretorio_projeto: str | Path = DIRETORIO_PROJETO,
    caminho_lock: str | Path | None = None,
) -> EstadoNode:
    diretorio_projeto = Path(diretorio_projeto).resolve()

    if caminho_lock is None:
        caminho_lock = diretorio_projeto / "execucao_em_andamento.lock"

    caminho_lock = Path(caminho_lock)

    processos = _listar_processos()

    processos_projeto = tuple(
        processo
        for processo in processos
        if _processo_pertence_projeto(
            processo,
            diretorio_projeto,
        )
    )

    metricas = _obter_metricas_sistema()

    (
        disco_total,
        disco_livre,
        disco_percentual,
    ) = _metricas_disco(diretorio_projeto)

    supervisor_pids = _buscar_pids(
        processos,
        diretorio_projeto,
        "supervisor_renda_automatica.ps1",
    )

    runtime_pids = _buscar_pids(
        processos,
        diretorio_projeto,
        str(diretorio_projeto / "runtime.py"),
    )

    social_pids = _buscar_pids(
        processos,
        diretorio_projeto,
        str(diretorio_projeto / "social_scout_telegram.py"),
    )

    bot_pids = _buscar_pids(
        processos,
        diretorio_projeto,
        str(diretorio_projeto / "bot_consulta.py"),
    )

    publicador_pids = _buscar_pids(
        processos,
        diretorio_projeto,
        str(diretorio_projeto / "publicador_fila.py"),
    )

    node_agent_pids = _buscar_pids(
        processos,
        diretorio_projeto,
        str(diretorio_projeto / "node_agent.py"),
    )

    chrome_pids = _buscar_chrome_cdp_pids(
        processos,
        diretorio_projeto,
    )

    cdp_disponivel = _cdp_esta_disponivel()

    servicos = (
        EstadoServicoNode(
            nome="supervisor",
            ativo=bool(supervisor_pids),
            pids=supervisor_pids,
            memoria_rss_bytes=(
                _somar_memoria_processos(
                    processos,
                    supervisor_pids,
                )
            ),
        ),
        EstadoServicoNode(
            nome="runtime",
            ativo=bool(runtime_pids),
            pids=runtime_pids,
            memoria_rss_bytes=(
                _somar_memoria_processos(
                    processos,
                    runtime_pids,
                )
            ),
        ),
        EstadoServicoNode(
            nome="social_scout",
            ativo=bool(social_pids),
            pids=social_pids,
            memoria_rss_bytes=(
                _somar_memoria_processos(
                    processos,
                    social_pids,
                )
            ),
        ),
        EstadoServicoNode(
            nome="bot_consulta",
            ativo=bool(bot_pids),
            pids=bot_pids,
            memoria_rss_bytes=(
                _somar_memoria_processos(
                    processos,
                    bot_pids,
                )
            ),
        ),
        EstadoServicoNode(
            nome="publicador_fila",
            ativo=bool(publicador_pids),
            pids=publicador_pids,
            memoria_rss_bytes=(
                _somar_memoria_processos(
                    processos,
                    publicador_pids,
                )
            ),
        ),
        EstadoServicoNode(
            nome="node_health_agent",
            ativo=bool(node_agent_pids),
            pids=node_agent_pids,
            memoria_rss_bytes=(
                _somar_memoria_processos(
                    processos,
                    node_agent_pids,
                )
            ),
        ),
        EstadoServicoNode(
            nome="chrome_cdp",
            ativo=(bool(chrome_pids) and cdp_disponivel),
            pids=chrome_pids,
            detalhes=("endpoint_funcional" if cdp_disponivel else "endpoint_indisponivel"),
            memoria_rss_bytes=(
                _somar_memoria_processos(
                    processos,
                    chrome_pids,
                )
            ),
        ),
        _estado_pipeline(
            processos,
            caminho_lock,
        ),
    )

    memoria_projeto = _somar_memoria_processos(processos_projeto)

    return EstadoNode(
        versao_schema=1,
        node_id=node_id,
        coletado_em=(datetime.now(UTC).isoformat()),
        sistema=platform.system(),
        versao_sistema=(platform.version()),
        arquitetura=(platform.machine()),
        uptime_segundos=(metricas.uptime_segundos),
        cpu_percentual=(metricas.cpu_percentual),
        memoria_total_bytes=(metricas.memoria_total_bytes),
        memoria_disponivel_bytes=(metricas.memoria_disponivel_bytes),
        memoria_uso_percentual=(metricas.memoria_uso_percentual),
        disco_total_bytes=disco_total,
        disco_livre_bytes=disco_livre,
        disco_uso_percentual=(disco_percentual),
        quantidade_processos_projeto=(len(processos_projeto)),
        servicos=servicos,
        memoria_processos_projeto_bytes=(memoria_projeto),
    )


def salvar_estado_node(
    estado: EstadoNode,
    caminho: str | Path = CAMINHO_ESTADO_PADRAO,
) -> Path:
    caminho = Path(caminho)

    caminho.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporario = caminho.with_suffix(caminho.suffix + ".tmp")

    temporario.write_text(
        json.dumps(
            estado.para_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    temporario.replace(caminho)

    return caminho
