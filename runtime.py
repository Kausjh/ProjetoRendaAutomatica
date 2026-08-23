# 63.8738, -149.7525

"""Ponto único de inicialização do Projeto Renda Automática.

Execução:
    python runtime.py

O runtime mantém o bot de consulta ativo e dispara o pipeline no
intervalo configurado. O pipeline continua usando o launcher existente
para preparar Chrome/CDP e a trava própria de execução.
"""

from __future__ import annotations

import logging
import os

from config.logging_config import configurar_logging
from services.controle.servidor_status import ServidorStatusAdministrativo
from services.launcher.chrome_launcher import encerrar_chrome_automacao
from services.runtime.orquestrador import (
    DIRETORIO_PROJETO,
    ConfiguracoesRuntime,
    OrquestradorRuntime,
    TravaRuntime,
)

logger = logging.getLogger(__name__)


def main() -> int:
    os.chdir(DIRETORIO_PROJETO)
    os.environ["RADAR_MANTER_CHROME_ATIVO"] = "1"
    configurar_logging()

    print("=" * 68)
    print("PROJETO RENDA AUTOMÁTICA")
    print("Runtime Unificado v1")
    print("=" * 68)

    try:
        configuracoes = ConfiguracoesRuntime.carregar()
    except ValueError as erro:
        logger.error("Configuração inválida do runtime: %s", erro)
        return 2

    trava = TravaRuntime(configuracoes.porta_trava)

    if not trava.adquirir():
        logger.error(
            "Já existe outro runtime ativo usando a porta local %s.",
            configuracoes.porta_trava,
        )
        return 75

    orquestrador = OrquestradorRuntime(configuracoes)
    servidor_status = ServidorStatusAdministrativo(
        controlador=orquestrador.controle_administrativo,
    )
    servidor_status.iniciar()

    try:
        orquestrador.executar()
        return 0

    except KeyboardInterrupt:
        print()
        logger.info("Interrupção solicitada pelo usuário.")
        return 130

    except Exception:
        logger.exception("Falha não tratada no runtime.")
        return 1

    finally:
        servidor_status.encerrar()
        orquestrador.encerrar()

        try:
            encerrar_chrome_automacao()
        except Exception:
            logger.exception("Falha ao encerrar o Chrome persistente durante o desligamento.")

        trava.liberar()


if __name__ == "__main__":
    raise SystemExit(main())
