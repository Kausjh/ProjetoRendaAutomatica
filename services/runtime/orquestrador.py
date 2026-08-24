# 63.8738, -149.7525

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from config.configuracoes import Configuracoes
from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.controle.controlador import ControladorAdministrativo
from services.launcher.chrome_launcher import (
    encerrar_chrome_automacao,
    preparar_chrome,
)

logger = logging.getLogger(__name__)

DIRETORIO_PROJETO: Final = Path(__file__).resolve().parents[2]
ARQUIVO_BOT_CONSULTA: Final = DIRETORIO_PROJETO / "bot_consulta.py"
ARQUIVO_PUBLICADOR_FILA: Final = DIRETORIO_PROJETO / "publicador_fila.py"
ARQUIVO_LAUNCHER_PIPELINE: Final = (
    DIRETORIO_PROJETO / "services" / "launcher" / "chrome_launcher.py"
)

CODIGO_SAIDA_JA_EM_EXECUCAO: Final = 75
CODIGO_SAIDA_REDE_INDISPONIVEL: Final = 76
TEMPO_LIMITE_ENCERRAMENTO: Final = 8.0

HOST_TELEGRAM: Final = "api.telegram.org"
HOST_MERCADO_LIVRE: Final = "www.mercadolivre.com.br"
PORTA_HTTPS: Final = 443


@dataclass(frozen=True, slots=True)
class ConfiguracoesRuntime:
    intervalo_minutos: float = 30.0
    executar_ao_iniciar: bool = True
    reiniciar_bot: bool = True
    intervalo_monitoramento_segundos: float = 2.0
    atraso_reinicio_bot_segundos: float = 5.0

    aguardar_internet_ao_iniciar: bool = True
    intervalo_verificacao_rede_segundos: float = 10.0
    timeout_verificacao_rede_segundos: float = 3.0

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
            aguardar_internet_ao_iniciar=_buscar_booleano(
                "RUNTIME_AGUARDAR_INTERNET_AO_INICIAR",
                True,
            ),
            intervalo_verificacao_rede_segundos=_buscar_decimal(
                "RUNTIME_INTERVALO_VERIFICACAO_REDE_SEGUNDOS",
                10.0,
            ),
            timeout_verificacao_rede_segundos=_buscar_decimal(
                "RUNTIME_TIMEOUT_VERIFICACAO_REDE_SEGUNDOS",
                3.0,
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
            raise ValueError("RUNTIME_ATRASO_REINICIO_BOT_SEGUNDOS nÃ£o pode ser negativo.")

        if self.intervalo_verificacao_rede_segundos <= 0:
            raise ValueError(
                "RUNTIME_INTERVALO_VERIFICACAO_REDE_SEGUNDOS " "precisa ser maior que zero."
            )

        if self.timeout_verificacao_rede_segundos <= 0:
            raise ValueError(
                "RUNTIME_TIMEOUT_VERIFICACAO_REDE_SEGUNDOS " "precisa ser maior que zero."
            )

        if not 1024 <= self.porta_trava <= 65535:
            raise ValueError("RUNTIME_PORTA_TRAVA precisa estar entre 1024 e 65535.")


class TravaRuntime:
    """Trava de processo baseada em porta TCP local.

    Enquanto o runtime estiver vivo, ele mantÃ©m a porta reservada.
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

        self.repositorio_admin = ControleAdministrativoRepository()
        self._lock_administrativo = threading.RLock()
        self._publicador_pausado = self.repositorio_admin.obter_booleano(
            "publicador_pausado",
            False,
        )
        self._pipeline_imediato_pendente = False
        self._reinicio_chrome_em_andamento = False

        # Estado de conectividade usado para registrar apenas transiÃ§Ãµes,
        # evitando repetir o mesmo aviso a cada ciclo de monitoramento.
        self._estado_conectividade: dict[str, bool | None] = {
            "internet": None,
            "telegram": None,
            "mercado_livre": None,
        }

        self.controle_administrativo = ControladorAdministrativo(
            self,
            repositorio_admin=self.repositorio_admin,
        )

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
            raise FileNotFoundError(
                f"Arquivos obrigatÃ³rios do runtime nÃ£o encontrados: {arquivos}"
            )

        # TambÃ©m valida as variÃ¡veis obrigatÃ³rias e todas as regras
        # existentes do projeto.
        Configuracoes()

    def servico_tcp_disponivel(
        self,
        host: str,
        porta: int = PORTA_HTTPS,
    ) -> bool:
        """Testa DNS + conexÃ£o TCP curta sem fazer requisiÃ§Ã£o HTTP."""

        try:
            with socket.create_connection(
                (host, porta),
                timeout=self.configuracoes.timeout_verificacao_rede_segundos,
            ):
                return True
        except OSError:
            return False

    def internet_disponivel(self) -> bool:
        """Considera a internet disponÃvel se ao menos um serviÃ§o responder."""

        return self.servico_tcp_disponivel(HOST_TELEGRAM) or self.servico_tcp_disponivel(
            HOST_MERCADO_LIVRE
        )

    def telegram_disponivel(self) -> bool:
        return self.servico_tcp_disponivel(HOST_TELEGRAM)

    def mercado_livre_disponivel(self) -> bool:
        return self.servico_tcp_disponivel(HOST_MERCADO_LIVRE)

    def _registrar_estado_conectividade(
        self,
        nome: str,
        disponivel: bool,
        mensagem_indisponivel: str,
        mensagem_restabelecida: str,
    ) -> None:
        estado_anterior = self._estado_conectividade.get(nome)

        if estado_anterior is disponivel:
            return

        self._estado_conectividade[nome] = disponivel

        if disponivel:
            if estado_anterior is False:
                logger.info(mensagem_restabelecida)
            return

        logger.warning(mensagem_indisponivel)

    def verificar_internet(self) -> bool:
        disponivel = self.internet_disponivel()

        self._registrar_estado_conectividade(
            nome="internet",
            disponivel=disponivel,
            mensagem_indisponivel=(
                "Internet ainda nÃ£o estÃ¡ disponÃvel. "
                "O runtime permanecerÃ¡ ativo e tentarÃ¡ novamente."
            ),
            mensagem_restabelecida=("Conectividade com a internet restabelecida."),
        )

        return disponivel

    def verificar_telegram(self) -> bool:
        disponivel = self.telegram_disponivel()

        self._registrar_estado_conectividade(
            nome="telegram",
            disponivel=disponivel,
            mensagem_indisponivel=(
                "Telegram indisponÃvel no momento. "
                "Bot e publicador nÃ£o serÃ£o reiniciados atÃ© o serviÃ§o voltar."
            ),
            mensagem_restabelecida=("Conectividade com o Telegram restabelecida."),
        )

        return disponivel

    def verificar_mercado_livre(self) -> bool:
        disponivel = self.mercado_livre_disponivel()

        self._registrar_estado_conectividade(
            nome="mercado_livre",
            disponivel=disponivel,
            mensagem_indisponivel=(
                "Mercado Livre indisponÃvel no momento. "
                "O prÃ³ximo ciclo ficarÃ¡ aguardando conectividade."
            ),
            mensagem_restabelecida=("Conectividade com o Mercado Livre restabelecida."),
        )

        return disponivel

    def aguardar_internet_inicial(self) -> None:
        if not self.configuracoes.aguardar_internet_ao_iniciar:
            return

        while not self._encerrando:
            if self.verificar_internet():
                return

            time.sleep(self.configuracoes.intervalo_verificacao_rede_segundos)

    def iniciar_bot(self) -> None:
        if self.processo_bot is not None and self.processo_bot.poll() is None:
            return

        if not self.verificar_telegram():
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
                "Bot de consulta encerrou com cÃ³digo %s.",
                processo.returncode,
            )

        if not self.configuracoes.reiniciar_bot:
            return

        if not self.verificar_telegram():
            return

        if self.configuracoes.atraso_reinicio_bot_segundos > 0:
            logger.info(
                "Reiniciando bot em %.1f segundo(s).",
                self.configuracoes.atraso_reinicio_bot_segundos,
            )
            time.sleep(self.configuracoes.atraso_reinicio_bot_segundos)

        self.iniciar_bot()

    def iniciar_publicador(self) -> None:
        if self._publicador_pausado:
            return

        if self.processo_publicador is not None and self.processo_publicador.poll() is None:
            return

        if not self.verificar_telegram():
            return

        logger.info("Iniciando publicador contÃnuo da fila.")

        self.processo_publicador = subprocess.Popen(
            [sys.executable, str(ARQUIVO_PUBLICADOR_FILA)],
            cwd=DIRETORIO_PROJETO,
        )

        logger.info(
            "Publicador da fila iniciado com PID %s.",
            self.processo_publicador.pid,
        )

    def garantir_publicador_ativo(self) -> None:
        if self._encerrando or self._publicador_pausado:
            return

        processo = self.processo_publicador

        if processo is not None and processo.poll() is None:
            return

        if processo is not None:
            logger.error(
                "Publicador da fila encerrou com cÃ³digo %s.",
                processo.returncode,
            )

        if not self.verificar_telegram():
            return

        if self.configuracoes.atraso_reinicio_bot_segundos > 0:
            logger.info(
                "Reiniciando publicador em %.1f segundo(s).",
                self.configuracoes.atraso_reinicio_bot_segundos,
            )
            time.sleep(self.configuracoes.atraso_reinicio_bot_segundos)

        self.iniciar_publicador()

    @property
    def publicador_pausado(self) -> bool:
        return self._publicador_pausado

    @property
    def pipeline_imediato_pendente(self) -> bool:
        return self._pipeline_imediato_pendente

    @property
    def reinicio_chrome_em_andamento(self) -> bool:
        return self._reinicio_chrome_em_andamento

    def pausar_publicador(self) -> str:
        with self._lock_administrativo:
            if self._publicador_pausado:
                return "ja_pausado"

            self._publicador_pausado = True
            self.repositorio_admin.definir_booleano(
                "publicador_pausado",
                True,
            )

            processo = self.processo_publicador
            self._encerrar_processo(
                processo=processo,
                nome="publicador da fila",
            )
            self.processo_publicador = None

        logger.warning("Publicador pausado por acao administrativa.")
        return "pausado"

    def retomar_publicador(self) -> str:
        with self._lock_administrativo:
            if not self._publicador_pausado:
                return "ja_liberado"

            self._publicador_pausado = False
            self.repositorio_admin.definir_booleano(
                "publicador_pausado",
                False,
            )

        logger.info("Pausa administrativa do publicador removida.")
        self.iniciar_publicador()

        if self.processo_publicador is not None and self.processo_publicador.poll() is None:
            return "retomado"

        return "liberado_aguardando_condicoes"

    def solicitar_pipeline_imediato(self) -> str:
        with self._lock_administrativo:
            processo = self.processo_pipeline

            if processo is not None and processo.poll() is None:
                return "pipeline_em_execucao"

            if self._pipeline_imediato_pendente:
                return "ja_solicitado"

            self._pipeline_imediato_pendente = True

        logger.info("Execucao imediata do pipeline solicitada administrativamente.")
        return "solicitado"

    def reiniciar_bot_administrativamente(self) -> str:
        with self._lock_administrativo:
            processo = self.processo_bot
            self._encerrar_processo(
                processo=processo,
                nome="bot de consulta",
            )
            self.processo_bot = None

        logger.warning("Reinicio do bot solicitado administrativamente.")
        self.iniciar_bot()

        if self.processo_bot is not None and self.processo_bot.poll() is None:
            return "reiniciado"

        return "aguardando_telegram"

    def solicitar_reinicio_chrome(self) -> str:
        with self._lock_administrativo:
            if self._reinicio_chrome_em_andamento:
                return "ja_em_andamento"

            self._reinicio_chrome_em_andamento = True

        thread = threading.Thread(
            target=self._reiniciar_chrome_worker,
            name="reinicio-chrome-administrativo",
            daemon=True,
        )
        thread.start()

        logger.warning("Reinicio do Chrome/CDP solicitado administrativamente.")
        return "solicitado"

    def _reiniciar_chrome_worker(self) -> None:
        try:
            encerrar_chrome_automacao()
            preparar_chrome()
            logger.info("Chrome/CDP reiniciado administrativamente com sucesso.")
        except Exception:
            logger.exception("Falha ao reiniciar Chrome/CDP administrativamente.")
        finally:
            with self._lock_administrativo:
                self._reinicio_chrome_em_andamento = False

    def suspender_servicos_telegram(self) -> None:
        """Encerra filhos do Telegram rapidamente durante queda de rede."""

        havia_bot = self.processo_bot is not None and self.processo_bot.poll() is None
        havia_publicador = (
            self.processo_publicador is not None and self.processo_publicador.poll() is None
        )

        if not havia_bot and not havia_publicador:
            return

        logger.warning(
            "Telegram/rede indisponÃvel durante a execuÃ§Ã£o. "
            "Suspendendo bot e publicador para evitar tempestade de erros."
        )

        self._encerrar_processo(
            processo=self.processo_publicador,
            nome="publicador da fila",
        )
        self._encerrar_processo(
            processo=self.processo_bot,
            nome="bot de consulta",
        )

        self.processo_publicador = None
        self.processo_bot = None

    def interromper_pipeline_por_rede(self) -> None:
        processo = self.processo_pipeline

        if processo is None or processo.poll() is not None:
            return

        logger.warning(
            "Conectividade com o Mercado Livre foi perdida durante "
            "o ciclo. Interrompendo o pipeline atual com seguranÃ§a; "
            "o ciclo serÃ¡ refeito quando a rede voltar."
        )

        self._encerrar_processo(
            processo=processo,
            nome="pipeline",
        )

    def aguardar_rede_restabelecer(self) -> None:
        """MantÃ©m o runtime vivo atÃ© a rede necessÃ¡ria voltar."""

        logger.info(
            "Runtime em modo de espera por rede. "
            "Nenhum novo ciclo serÃ¡ iniciado atÃ© a conectividade voltar."
        )

        while not self._encerrando:
            internet_ok = self.verificar_internet()
            telegram_ok = self.verificar_telegram()
            mercado_livre_ok = self.verificar_mercado_livre()

            if internet_ok and mercado_livre_ok:
                if telegram_ok:
                    self.iniciar_bot()
                    self.iniciar_publicador()

                logger.info(
                    "Rede restabelecida. O ciclo interrompido serÃ¡ "
                    "executado novamente desde o inÃcio."
                )
                return

            time.sleep(self.configuracoes.intervalo_verificacao_rede_segundos)

    def executar_pipeline(self) -> int:
        # MantÃ©m compatibilidade: se jÃ¡ estiver offline ANTES de iniciar,
        # o scheduler externo segura o ciclo. Este mÃ©todo apenas nÃ£o inicia.
        if not self.verificar_mercado_livre():
            return 0

        logger.info("Iniciando ciclo do pipeline.")

        self.processo_pipeline = subprocess.Popen(
            [sys.executable, str(ARQUIVO_LAUNCHER_PIPELINE)],
            cwd=DIRETORIO_PROJETO,
        )

        inicio = time.monotonic()
        interrompido_por_rede = False

        try:
            while self.processo_pipeline.poll() is None:
                telegram_ok = self.verificar_telegram()
                mercado_livre_ok = self.verificar_mercado_livre()

                if not telegram_ok:
                    self.suspender_servicos_telegram()
                else:
                    self.garantir_bot_ativo()
                    self.garantir_publicador_ativo()

                if not mercado_livre_ok:
                    interrompido_por_rede = True
                    self.interromper_pipeline_por_rede()
                    break

                time.sleep(self.configuracoes.intervalo_monitoramento_segundos)

            if interrompido_por_rede:
                codigo_saida = CODIGO_SAIDA_REDE_INDISPONIVEL
            else:
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
                "Ciclo ignorado porque jÃ¡ havia outra execuÃ§Ã£o do pipeline em andamento."
            )
        elif codigo_saida == CODIGO_SAIDA_REDE_INDISPONIVEL:
            logger.warning(
                (
                    "Ciclo interrompido por perda de conectividade apÃ³s "
                    "%.1f segundo(s). Nenhum horÃ¡rio serÃ¡ consumido."
                ),
                duracao,
            )
            self.suspender_servicos_telegram()
            self.aguardar_rede_restabelecer()
        else:
            logger.error(
                "Ciclo do pipeline terminou com cÃ³digo %s apÃ³s %.1f segundo(s).",
                codigo_saida,
                duracao,
            )

        return codigo_saida

    def executar(self) -> None:
        self.validar_ambiente()

        logger.info("Ambiente e configuraÃ§Ãµes validados.")
        logger.info(
            "Runtime configurado para executar o pipeline a cada %.1f minuto(s).",
            self.configuracoes.intervalo_minutos,
        )

        if self.configuracoes.aguardar_internet_ao_iniciar:
            logger.info(
                "InicializaÃ§Ã£o resiliente de rede ativa: "
                "aguardando conectividade antes de iniciar serviÃ§os."
            )

        self.aguardar_internet_inicial()

        if self._encerrando:
            return

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

            if self._pipeline_imediato_pendente:
                if not self.verificar_internet():
                    time.sleep(self.configuracoes.intervalo_verificacao_rede_segundos)
                    continue

                if not self.verificar_mercado_livre():
                    time.sleep(self.configuracoes.intervalo_verificacao_rede_segundos)
                    continue

                self._pipeline_imediato_pendente = False
                codigo_ciclo = self.executar_pipeline()

                if codigo_ciclo == CODIGO_SAIDA_REDE_INDISPONIVEL:
                    self._pipeline_imediato_pendente = True
                    continue

                proxima_execucao = time.monotonic() + intervalo_segundos

                logger.info(
                    "Ciclo administrativo concluido. Proximo ciclo em %.1f minuto(s).",
                    intervalo_segundos / 60.0,
                )
                continue

            agora = time.monotonic()

            if agora >= proxima_execucao:
                if not self.verificar_internet():
                    time.sleep(self.configuracoes.intervalo_verificacao_rede_segundos)
                    continue

                if not self.verificar_mercado_livre():
                    time.sleep(self.configuracoes.intervalo_verificacao_rede_segundos)
                    continue

                inicio_agendado = proxima_execucao

                codigo_ciclo = self.executar_pipeline()

                if codigo_ciclo == CODIGO_SAIDA_REDE_INDISPONIVEL:
                    # O ciclo caiu no meio por rede. Mantemos o mesmo horÃ¡rio
                    # vencido e refazemos imediatamente apÃ³s a recuperaÃ§Ã£o.
                    continue

                proxima_execucao = calcular_proxima_execucao(
                    execucao_anterior=inicio_agendado,
                    agora=time.monotonic(),
                    intervalo_segundos=intervalo_segundos,
                )

                espera = max(0.0, proxima_execucao - time.monotonic())

                logger.info(
                    "PrÃ³ximo ciclo em aproximadamente %.1f minuto(s).",
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

        if os.name == "nt":
            resultado = subprocess.run(
                [
                    "taskkill",
                    "/PID",
                    str(processo.pid),
                    "/T",
                    "/F",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            try:
                processo.wait(timeout=TEMPO_LIMITE_ENCERRAMENTO)
            except subprocess.TimeoutExpired:
                logger.warning(
                    (
                        "%s ainda aparece ativo após taskkill /T /F; "
                        "tentando encerramento direto."
                    ),
                    nome,
                )
                processo.kill()
                processo.wait(timeout=TEMPO_LIMITE_ENCERRAMENTO)

            if resultado.returncode == 0:
                logger.info(
                    "Árvore de processos de %s encerrada com sucesso.",
                    nome,
                )
            else:
                saida = (resultado.stderr or resultado.stdout or "").strip()
                logger.warning(
                    "taskkill retornou código %s ao encerrar %s: %s",
                    resultado.returncode,
                    nome,
                    saida or "sem detalhes",
                )

            return

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
    """Calcula o prÃ³ximo horÃ¡rio sem acumular ciclos atrasados.

    Se um ciclo demorar mais que o intervalo, horÃ¡rios que jÃ¡ passaram
    sÃ£o pulados. Assim nunca existem duas execuÃ§Ãµes simultÃ¢neas porque
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
        raise ValueError(f"{nome} precisa ser um nÃºmero.") from erro


def _buscar_inteiro(nome: str, valor_padrao: int) -> int:
    valor = os.getenv(nome)

    if valor is None:
        return valor_padrao

    try:
        return int(valor)
    except ValueError as erro:
        raise ValueError(f"{nome} precisa ser um nÃºmero inteiro.") from erro
