# 63.8738, -149.7525

from __future__ import annotations

import argparse
import logging
import os
import signal

from dotenv import load_dotenv

from config.logging_config import configurar_logging
from services.scout.partner_scout_worker import (
    INTERVALO_PADRAO_SEGUNDOS,
    PartnerScoutWorker,
    criar_partner_scout_worker,
)

logger = logging.getLogger(__name__)


def _intervalo_configurado() -> float:
    valor = os.getenv("PARTNER_SCOUT_INTERVALO_SEGUNDOS")

    if valor is None:
        return INTERVALO_PADRAO_SEGUNDOS

    try:
        intervalo = float(valor)

    except ValueError as erro:
        raise ValueError("PARTNER_SCOUT_INTERVALO_SEGUNDOS " "deve ser numerico.") from erro

    if intervalo <= 0:
        raise ValueError("PARTNER_SCOUT_INTERVALO_SEGUNDOS " "deve ser maior que zero.")

    return intervalo


def _argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=("Worker continuo do Partner Scout."))

    parser.add_argument(
        "--once",
        action="store_true",
        help=("Executa um unico ciclo " "e encerra."),
    )

    return parser.parse_args()


def _instalar_sinais(
    worker: PartnerScoutWorker,
) -> None:
    def solicitar_parada(
        numero_sinal: int,
        frame: object,
    ) -> None:
        del frame

        logger.info(
            "Sinal %s recebido pelo Partner Scout.",
            numero_sinal,
        )

        worker.solicitar_parada()

    for nome_sinal in (
        "SIGINT",
        "SIGTERM",
        "SIGBREAK",
    ):
        valor_sinal = getattr(
            signal,
            nome_sinal,
            None,
        )

        if valor_sinal is None:
            continue

        try:
            signal.signal(
                valor_sinal,
                solicitar_parada,
            )

        except (
            OSError,
            RuntimeError,
            ValueError,
        ):
            pass


def main() -> int:
    load_dotenv(
        ".env",
        override=True,
    )

    configurar_logging()

    argumentos = _argumentos()

    try:
        intervalo = _intervalo_configurado()

    except ValueError as erro:
        logger.error(
            "Configuracao invalida do " "Partner Scout: %s",
            erro,
        )

        return 2

    worker = criar_partner_scout_worker(intervalo_segundos=intervalo)

    _instalar_sinais(worker)

    maximo_ciclos = 1 if argumentos.once else None

    worker.executar(maximo_ciclos=maximo_ciclos)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
