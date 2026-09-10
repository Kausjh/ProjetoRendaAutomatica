# 63.8738, -149.7525

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from models.estado_node import EstadoNode
from services.infra.node_health import (
    CAMINHO_ESTADO_PADRAO,
    DIRETORIO_PROJETO,
    capturar_estado_node,
    salvar_estado_node,
)
from services.infra.node_identity import (
    obter_ou_criar_node_id,
)

logger = logging.getLogger(__name__)

INTERVALO_PADRAO_SEGUNDOS = 300.0

DIRETORIO_HISTORICO_PADRAO = DIRETORIO_PROJETO / "data" / "node" / "historico"


class NodeHealthAgent:
    def __init__(
        self,
        intervalo_segundos: float = (INTERVALO_PADRAO_SEGUNDOS),
        *,
        caminho_estado: str | Path = (CAMINHO_ESTADO_PADRAO),
        diretorio_historico: str | Path = (DIRETORIO_HISTORICO_PADRAO),
        obter_node_id: Callable[
            [],
            str,
        ] = obter_ou_criar_node_id,
        capturar_estado: Callable[
            ...,
            EstadoNode,
        ] = capturar_estado_node,
        salvar_estado: Callable[
            ...,
            Path,
        ] = salvar_estado_node,
    ) -> None:
        intervalo_segundos = float(intervalo_segundos)

        if intervalo_segundos <= 0:
            raise ValueError("intervalo_segundos precisa " "ser maior que zero.")

        self.intervalo_segundos = intervalo_segundos

        self.caminho_estado = Path(caminho_estado)

        self.diretorio_historico = Path(diretorio_historico)

        self._obter_node_id = obter_node_id

        self._capturar_estado = capturar_estado

        self._salvar_estado = salvar_estado

        self._parada = threading.Event()

    def solicitar_parada(self) -> None:
        self._parada.set()

    def executar_ciclo(self) -> EstadoNode:
        node_id = self._obter_node_id()

        estado = self._capturar_estado(node_id=node_id)

        self._salvar_estado(
            estado,
            self.caminho_estado,
        )

        self._registrar_historico(estado)

        return estado

    def executar(
        self,
        maximo_ciclos: int | None = None,
    ) -> int:
        if maximo_ciclos is not None and maximo_ciclos <= 0:
            raise ValueError("maximo_ciclos precisa " "ser maior que zero.")

        ciclos = 0

        logger.info(
            "Node Health Agent iniciado " "com intervalo de %.2f segundos.",
            self.intervalo_segundos,
        )

        while not self._parada.is_set():
            try:
                self.executar_ciclo()

            except Exception:
                logger.exception("Falha durante coleta " "do Node Health.")

            ciclos += 1

            if maximo_ciclos is not None and ciclos >= maximo_ciclos:
                break

            if self._parada.wait(self.intervalo_segundos):
                break

        logger.info("Node Health Agent encerrado.")

        return ciclos

    def _registrar_historico(
        self,
        estado: EstadoNode,
    ) -> Path:
        try:
            instante = datetime.fromisoformat(estado.coletado_em)
        except ValueError as erro:
            raise ValueError("coletado_em do estado " "possui formato invalido.") from erro

        data = instante.date().isoformat()

        caminho = self.diretorio_historico / f"{data}.jsonl"

        caminho.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        linha = json.dumps(
            estado.para_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
        )

        with caminho.open(
            "a",
            encoding="utf-8",
        ) as arquivo:
            arquivo.write(linha)
            arquivo.write("\n")

        return caminho
