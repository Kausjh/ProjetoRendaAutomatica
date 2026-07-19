from datetime import datetime
import logging
from pathlib import Path


def configurar_logging() -> None:
    pasta_logs = Path("logs")

    pasta_logs.mkdir(
        parents=True,
        exist_ok=True
    )

    data_atual = datetime.now().strftime(
        "%Y-%m-%d"
    )

    caminho_log = pasta_logs / (
        f"{data_atual}.log"
    )

    formato = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    logger_raiz = logging.getLogger()

    logger_raiz.setLevel(
        logging.INFO
    )

    logger_raiz.handlers.clear()

    terminal = logging.StreamHandler()

    terminal.setFormatter(
        formato
    )

    arquivo = logging.FileHandler(
        filename=caminho_log,
        mode="a",
        encoding="utf-8"
    )

    arquivo.setFormatter(
        formato
    )

    logger_raiz.addHandler(
        terminal
    )

    logger_raiz.addHandler(
        arquivo
    )

    logging.getLogger(
        "httpx"
    ).setLevel(
        logging.WARNING
    )

    logging.getLogger(
        "httpcore"
    ).setLevel(
        logging.WARNING
    )

    logging.getLogger(
        "telegram"
    ).setLevel(
        logging.WARNING
    )