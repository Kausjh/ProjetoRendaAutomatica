# 63.8738, -149.7525

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from services.push_dispatcher_service import PushDispatcherService

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResultadoCicloPushDispatcherRuntime:
    recibos_status: str
    envios_processados: int
    ultimo_envio_status: str | None


class PushDispatcherRuntimeWorker:
    def __init__(
        self,
        *,
        dispatcher: PushDispatcherService,
        intervalo_segundos: float = 2.0,
        receipt_min_age_segundos: int = 900,
        max_envios_por_ciclo: int = 10,
    ) -> None:
        if intervalo_segundos <= 0:
            raise ValueError("intervalo_segundos precisa ser positivo.")
        if receipt_min_age_segundos < 0:
            raise ValueError("receipt_min_age_segundos nao pode ser negativo.")
        if max_envios_por_ciclo < 1:
            raise ValueError("max_envios_por_ciclo precisa ser positivo.")

        self.dispatcher = dispatcher
        self.intervalo_segundos = float(intervalo_segundos)
        self.receipt_min_age_segundos = int(receipt_min_age_segundos)
        self.max_envios_por_ciclo = int(max_envios_por_ciclo)

    def _corte_receipts(self) -> str:
        agora = datetime.now(UTC)
        corte = agora - timedelta(seconds=self.receipt_min_age_segundos)
        return corte.isoformat()

    def executar_ciclo(self) -> ResultadoCicloPushDispatcherRuntime:
        recibos = self.dispatcher.processar_recibos_pendentes(
            criado_ate=self._corte_receipts(),
        )

        envios_processados = 0
        ultimo_status: str | None = None

        for _ in range(self.max_envios_por_ciclo):
            resultado = self.dispatcher.processar_proximo_envio()
            ultimo_status = resultado.status

            if resultado.status == "sem_item":
                break

            envios_processados += 1

            if resultado.status == "retry_provider":
                break

        return ResultadoCicloPushDispatcherRuntime(
            recibos_status=recibos.status,
            envios_processados=envios_processados,
            ultimo_envio_status=ultimo_status,
        )

    def executar(
        self,
        *,
        stop_event: threading.Event | None = None,
    ) -> None:
        parada = stop_event or threading.Event()

        logger.info(
            "Push Dispatcher Runtime iniciado: intervalo=%.1fs | "
            "receipt_min_age=%ss | max_envios_ciclo=%s.",
            self.intervalo_segundos,
            self.receipt_min_age_segundos,
            self.max_envios_por_ciclo,
        )

        while not parada.is_set():
            try:
                resultado = self.executar_ciclo()
            except Exception:
                logger.exception("Falha isolada no ciclo do Push Dispatcher Runtime.")
            else:
                if resultado.envios_processados > 0 or resultado.recibos_status != "sem_recibos":
                    logger.info(
                        "Push Dispatcher Runtime: receipts=%s | envios=%s | ultimo=%s.",
                        resultado.recibos_status,
                        resultado.envios_processados,
                        resultado.ultimo_envio_status,
                    )

            parada.wait(self.intervalo_segundos)

        logger.info("Push Dispatcher Runtime encerrado.")
