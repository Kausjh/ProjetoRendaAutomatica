# 63.8738, -149.7525

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from config.configuracoes import Configuracoes

logger = logging.getLogger(__name__)

DIRETORIO_PROJETO: Final = Path(__file__).resolve().parents[2]
ARQUIVO_BOT_CONSULTA: Final = DIRETORIO_PROJETO / "bot_consulta.py"
ARQUIVO_PUBLICADOR_FILA: Final = DIRETORIO_PROJETO / "publicador_fila.py"
ARQUIVO_LAUNCHER_PIPELINE: Final = (
    DIRETORIO_PROJETO / "services" / "launcher" / "chrome_launcher.py"
)

CODIGO_SAIDA_JA_EM_EXECUCAO: Final = 75
TEMPO_LIMITE_ENCERRAMENTO: Final = 8.0


@dataclass(frozen=True, slots=True)
class ConfiguracoesRuntime:
    intervalo_minutos: float = 30.0
    executar_ao_iniciar: bool = True
    reiniciar_bot: bool = True
    intervalo_monitoramento_segundos: float = 2.0
    atraso_reinicio_bot_segundos: float = 5.0
    porta_trava: int = 48731

    @classmethod
    def carregar(cls) -> ConfiguracoesRuntime:
        configuracao = cls(
            intervalo_minutos=_buscar_decimal(
                "RUNTIME_INTERVALO_MINUTOS",
                30.0,
            ),
            executar_ao_iniciar=_buscar_booleano(
                "RUNTIME_EXECUTAR_AO_INICIAR",
                True,
            ),
            reiniciar_bot=_buscar_booleano(
                "RUNTIME_REINICIAR_BOT",
                True,
            ),
            intervalo_monitoramento_segundos=_buscar_decimal(
                "RUNTIME_INTERVALO_MONITORAMENTO_SEGUNDOS",
                2.0,
            ),
            atraso_reinicio_bot_segundos=_buscar_decimal(
                "RUNTIME_ATRASO_REINICIO_BOT_SEGUNDOS",
                5.0,
            ),
            porta_trava=_buscar_inteiro(
                "RUNTIME_PORTA_TRAVA",
                48731,
            ),
        )

        configuracao.validar()

        return configuracao

    def validar(self) -> None:
        if self.intervalo_minutos <= 0:
            raise ValueError("RUNTIME_INTERVALO_MINUTOS precisa ser maior que zero.")

        if self.intervalo_monitoramento_segundos <= 0:
            raise ValueError("RUNTIME_INTERVALO_MONITORAMENTO_SEGUNDOS precisa ser maior que zero.")

        if self.atraso_reinicio_bot_segundos < 0:
            raise ValueError("RUNTIME_ATRASO_REINICIO_BOT_SEGUNDOS não pode ser negativo.")

        if not 1024 <= self.porta_trava <= 65535:
            raise ValueError("RUNTIME_PORTA_TRAVA precisa estar entre 1024 e 65535.")


class TravaRuntime:
    """Trava de processo baseada em porta TCP local.

    Enquanto o runtime estiver vivo, ele mantém a porta reservada.
    Se o processo morrer, o sistema operacional libera a porta
    automaticamente, evitando arquivos de trava abandonados.
    """

    def __init__(self, porta: int) -> None:
        self.porta = porta
        self._socket: socket.socket | None = None

    def adquirir(self) -> bool:
        trava = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            trava.bind(("127.0.0.1", self.porta))
            trava.listen(1)
        except OSError:
            trava.close()
            return False

        self._socket = trava
        return True

    def liberar(self) -> None:
        if self._socket is None:
            return

        try:
            self._socket.close()
        finally:
            self._socket = None


class OrquestradorRuntime:
    def __init__(self, configuracoes: ConfiguracoesRuntime) -> None:
        self.configuracoes = configuracoes
        self.processo_bot: subprocess.Popen[bytes] | None = None
        self.processo_publicador: subprocess.Popen[bytes] | None = None
        self.processo_pipeline: subprocess.Popen[bytes] | None = None
        self._encerrando = False

    def validar_ambiente(self) -> None:
        faltando = [
            caminho
            for caminho in (
                ARQUIVO_BOT_CONSULTA,
                ARQUIVO_PUBLICADOR_FILA,
                ARQUIVO_LAUNCHER_PIPELINE,
                DIRETORIO_PROJETO / "main.py",
            )
            if not caminho.is_file()
        ]

        if faltando:
            arquivos = ", ".join(str(caminho) for caminho in faltando)
            raise FileNotFoundError(f"Arquivos obrigatórios do runtime não encontrados: {arquivos}")

        # Também valida as variáveis obrigatórias e todas as regras
        # existentes do projeto.
        Configuracoes()

    def iniciar_bot(self) -> None:
        if self.processo_bot is not None and self.processo_bot.poll() is None:
            return

        logger.info("Iniciando bot de consulta.")

        self.processo_bot = subprocess.Popen(
            [sys.executable, str(ARQUIVO_BOT_CONSULTA)],
            cwd=DIRETORIO_PROJETO,
        )

        logger.info("Bot de consulta iniciado com PID %s.", self.processo_bot.pid)

    def garantir_bot_ativo(self) -> None:
        if self._encerrando:
            return

        processo = self.processo_bot

        if processo is not None and processo.poll() is None:
            return

        if processo is not None:
            logger.error(
                "Bot de consulta encerrou com código %s.",
                processo.returncode,
            )

        if not self.configuracoes.reiniciar_bot:
            return

        if self.configuracoes.atraso_reinicio_bot_segundos > 0:
            logger.info(
                "Reiniciando bot em %.1f segundo(s).",
                self.configuracoes.atraso_reinicio_bot_segundos,
            )
            time.sleep(self.configuracoes.atraso_reinicio_bot_segundos)

        self.iniciar_bot()

    def iniciar_publicador(self) -> None:
        if self.processo_publicador is not None and self.processo_publicador.poll() is None:
            return

        logger.info("Iniciando publicador contínuo da fila.")

        self.processo_publicador = subprocess.Popen(
            [sys.executable, str(ARQUIVO_PUBLICADOR_FILA)],
            cwd=DIRETORIO_PROJETO,
        )

        logger.info(
            "Publicador da fila iniciado com PID %s.",
            self.processo_publicador.pid,
        )

    def garantir_publicador_ativo(self) -> None:
        if self._encerrando:
            return

        processo = self.processo_publicador

        if processo is not None and processo.poll() is None:
            return

        if processo is not None:
            logger.error(
                "Publicador da fila encerrou com código %s.",
                processo.returncode,
            )

        if self.configuracoes.atraso_reinicio_bot_segundos > 0:
            logger.info(
                "Reiniciando publicador em %.1f segundo(s).",
                self.configuracoes.atraso_reinicio_bot_segundos,
            )
            time.sleep(self.configuracoes.atraso_reinicio_bot_segundos)

        self.iniciar_publicador()

    def executar_pipeline(self) -> int:
        logger.info("Iniciando ciclo do pipeline.")

        self.processo_pipeline = subprocess.Popen(
            [sys.executable, str(ARQUIVO_LAUNCHER_PIPELINE)],
            cwd=DIRETORIO_PROJETO,
        )

        inicio = time.monotonic()

        try:
            while self.processo_pipeline.poll() is None:
                self.garantir_bot_ativo()
                self.garantir_publicador_ativo()
                time.sleep(self.configuracoes.intervalo_monitoramento_segundos)

            codigo_saida = int(self.processo_pipeline.returncode or 0)
        finally:
            self.processo_pipeline = None

        duracao = time.monotonic() - inicio

        if codigo_saida == 0:
            logger.info(
                "Ciclo do pipeline finalizado com sucesso em %.1f segundo(s).",
                duracao,
            )
        elif codigo_saida == CODIGO_SAIDA_JA_EM_EXECUCAO:
            logger.warning(
                "Ciclo ignorado porque já havia outra execução do pipeline em andamento."
            )
        else:
            logger.error(
                "Ciclo do pipeline terminou com código %s após %.1f segundo(s).",
                codigo_saida,
                duracao,
            )

        return codigo_saida

    def executar(self) -> None:
        self.validar_ambiente()

        logger.info("Ambiente e configurações validados.")
        logger.info(
            "Runtime configurado para executar o pipeline a cada %.1f minuto(s).",
            self.configuracoes.intervalo_minutos,
        )

        self.iniciar_bot()
        self.iniciar_publicador()

        intervalo_segundos = self.configuracoes.intervalo_minutos * 60.0

        if self.configuracoes.executar_ao_iniciar:
            proxima_execucao = time.monotonic()
        else:
            proxima_execucao = time.monotonic() + intervalo_segundos

        while not self._encerrando:
            self.garantir_bot_ativo()
            self.garantir_publicador_ativo()

            agora = time.monotonic()

            if agora >= proxima_execucao:
                inicio_agendado = proxima_execucao

                self.executar_pipeline()

                proxima_execucao = calcular_proxima_execucao(
                    execucao_anterior=inicio_agendado,
                    agora=time.monotonic(),
                    intervalo_segundos=intervalo_segundos,
                )

                espera = max(0.0, proxima_execucao - time.monotonic())

                logger.info(
                    "Próximo ciclo em aproximadamente %.1f minuto(s).",
                    espera / 60.0,
                )

                continue

            espera = min(
                self.configuracoes.intervalo_monitoramento_segundos,
                max(0.0, proxima_execucao - agora),
            )

            if espera > 0:
                time.sleep(espera)

    def encerrar(self) -> None:
        if self._encerrando:
            return

        self._encerrando = True

        logger.info("Encerrando runtime.")

        self._encerrar_processo(
            processo=self.processo_pipeline,
            nome="pipeline",
        )

        self._encerrar_processo(
            processo=self.processo_publicador,
            nome="publicador da fila",
        )

        self._encerrar_processo(
            processo=self.processo_bot,
            nome="bot de consulta",
        )

        self.processo_pipeline = None
        self.processo_publicador = None
        self.processo_bot = None

        logger.info("Runtime encerrado.")

    @staticmethod
    def _encerrar_processo(
        processo: subprocess.Popen[bytes] | None,
        nome: str,
    ) -> None:
        if processo is None or processo.poll() is not None:
            return

        logger.info("Encerrando %s (PID %s).", nome, processo.pid)

        processo.terminate()

        try:
            processo.wait(timeout=TEMPO_LIMITE_ENCERRAMENTO)
        except subprocess.TimeoutExpired:
            logger.warning(
                "%s não encerrou no prazo; forçando encerramento.",
                nome,
            )
            processo.kill()
            processo.wait(timeout=TEMPO_LIMITE_ENCERRAMENTO)


def calcular_proxima_execucao(
    execucao_anterior: float,
    agora: float,
    intervalo_segundos: float,
) -> float:
    """Calcula o próximo horário sem acumular ciclos atrasados.

    Se um ciclo demorar mais que o intervalo, horários que já passaram
    são pulados. Assim nunca existem duas execuções simultâneas porque
    o scheduler tentou "compensar" o atraso.
    """

    if intervalo_segundos <= 0:
        raise ValueError("intervalo_segundos precisa ser maior que zero.")

    proxima = execucao_anterior + intervalo_segundos

    while proxima <= agora:
        proxima += intervalo_segundos

    return proxima


def _buscar_booleano(nome: str, valor_padrao: bool) -> bool:
    valor = os.getenv(nome)

    if valor is None:
        return valor_padrao

    return valor.strip().casefold() in {"1", "true", "sim", "on", "yes"}


def _buscar_decimal(nome: str, valor_padrao: float) -> float:
    valor = os.getenv(nome)

    if valor is None:
        return valor_padrao

    try:
        return float(valor)
    except ValueError as erro:
        raise ValueError(f"{nome} precisa ser um número.") from erro


def _buscar_inteiro(nome: str, valor_padrao: int) -> int:
    valor = os.getenv(nome)

    if valor is None:
        return valor_padrao

    try:
        return int(valor)
    except ValueError as erro:
        raise ValueError(f"{nome} precisa ser um número inteiro.") from erro
