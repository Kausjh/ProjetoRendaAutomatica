# 63.8738, -149.7525

from __future__ import annotations

import argparse
import logging
import os
import signal

from config.logging_config import configurar_logging
from services.infra.node_agent import (
    INTERVALO_PADRAO_SEGUNDOS,
    NodeHealthAgent,
)

logger = logging.getLogger(__name__)


def _intervalo_configurado() -> float:
    valor = os.getenv("NODE_HEALTH_INTERVALO_SEGUNDOS")

    if valor is None:
        return INTERVALO_PADRAO_SEGUNDOS

    try:
        intervalo = float(valor)
    except ValueError as erro:
        raise ValueError("NODE_HEALTH_INTERVALO_SEGUNDOS " "precisa ser numerico.") from erro

    if intervalo <= 0:
        raise ValueError("NODE_HEALTH_INTERVALO_SEGUNDOS " "precisa ser maior que zero.")

    return intervalo


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=("Agente local de observabilidade " "do host."))

    parser.add_argument(
        "--once",
        action="store_true",
        help=("Executa apenas uma coleta " "e encerra."),
    )

    return parser.parse_args()


def main() -> int:
    configurar_logging()

    argumentos = _argumentos()

    try:
        intervalo = _intervalo_configurado()
    except ValueError as erro:
        logger.error(
            "Configuracao invalida " "do Node Health Agent: %s",
            erro,
        )
        return 2

    agente = NodeHealthAgent(intervalo_segundos=intervalo)

    def solicitar_parada(
        sinal: int,
        frame: object,
    ) -> None:
        del frame

        logger.info(
            "Sinal %s recebido pelo " "Node Health Agent.",
            sinal,
        )

        agente.solicitar_parada()

    for nome_sinal in (
        "SIGINT",
        "SIGTERM",
        "SIGBREAK",
    ):
        sinal = getattr(
            signal,
            nome_sinal,
            None,
        )

        if sinal is None:
            continue

        try:
            signal.signal(
                sinal,
                solicitar_parada,
            )
        except (
            OSError,
            RuntimeError,
            ValueError,
        ):
            pass

    maximo_ciclos = 1 if argumentos.once else None

    agente.executar(maximo_ciclos=maximo_ciclos)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
