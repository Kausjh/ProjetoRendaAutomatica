# 63.8738, -149.7525

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Protocol

from models.sinal_scout import SinalScout
from repositories.sinais_scout_repository import (
    SinaisScoutRepository,
)

logger = logging.getLogger(__name__)


class SensorScout(Protocol):
    nome: str

    def buscar_sinais(
        self,
        updated_since: date | None = None,
    ) -> list[SinalScout]: ...


@dataclass(frozen=True, slots=True)
class ResultadoRadarScout:
    sinais_recebidos: int
    novos: int
    atualizados: int
    inalterados: int
    erros: int


class RadarScout:

    def __init__(
        self,
        sensores: list[SensorScout],
        repository: SinaisScoutRepository | None = None,
    ) -> None:
        self.sensores = sensores

        self.repository = repository or SinaisScoutRepository()

    def executar(
        self,
    ) -> ResultadoRadarScout:
        recebidos = 0
        novos = 0
        atualizados = 0
        inalterados = 0
        erros = 0

        for sensor in self.sensores:
            chave = "ultima_sincronizacao:" + sensor.nome

            ultima_data = self._parse_data(self.repository.obter_estado(chave))

            try:
                sinais = sensor.buscar_sinais(updated_since=ultima_data)

            except Exception:
                erros += 1

                logger.exception(
                    "Radar Scout: falha no sensor '%s'.",
                    sensor.nome,
                )

                continue

            recebidos += len(sinais)

            for sinal in sinais:
                resultado = self.repository.salvar(sinal)

                if resultado == "novo":
                    novos += 1

                elif resultado == "atualizado":
                    atualizados += 1

                else:
                    inalterados += 1

            hoje = datetime.now(UTC).date().isoformat()

            self.repository.salvar_estado(
                chave,
                hoje,
            )

        return ResultadoRadarScout(
            sinais_recebidos=recebidos,
            novos=novos,
            atualizados=atualizados,
            inalterados=inalterados,
            erros=erros,
        )

    @staticmethod
    def _parse_data(
        valor: str | None,
    ) -> date | None:
        if not valor:
            return None

        try:
            return date.fromisoformat(valor)

        except ValueError:
            return None
