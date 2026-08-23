# 63.8738, -149.7525

from __future__ import annotations

import os
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from services.controle.estado import (
    EstadoAdministrativo,
    EstadoConectividade,
    EstadoFila,
    EstadoProcesso,
)

if TYPE_CHECKING:
    from services.runtime.orquestrador import OrquestradorRuntime


class ProcessoGerenciado(Protocol):
    pid: int

    def poll(self) -> int | None: ...


class ControladorAdministrativo:
    """Expõe o estado operacional do runtime sem duplicar sua lógica."""

    def __init__(
        self,
        orquestrador: OrquestradorRuntime,
        fila: FilaPublicacaoRepository | None = None,
    ) -> None:
        self.orquestrador = orquestrador
        self.fila = fila or FilaPublicacaoRepository()

    @staticmethod
    def _estado_processo(
        processo: ProcessoGerenciado | None,
    ) -> EstadoProcesso:
        if processo is None:
            return EstadoProcesso(ativo=False, pid=None)

        ativo = processo.poll() is None

        return EstadoProcesso(
            ativo=ativo,
            pid=processo.pid if ativo else None,
        )

    def obter_estado(self) -> EstadoAdministrativo:
        resumo_fila = self.fila.resumo_familias_pendentes()

        conectividade = EstadoConectividade(
            internet=self.orquestrador.internet_disponivel(),
            telegram=self.orquestrador.telegram_disponivel(),
            mercado_livre=self.orquestrador.mercado_livre_disponivel(),
        )

        return EstadoAdministrativo(
            runtime_ativo=not self.orquestrador._encerrando,
            runtime_pid=os.getpid(),
            encerrando=self.orquestrador._encerrando,
            pipeline=self._estado_processo(self.orquestrador.processo_pipeline),
            publicador=self._estado_processo(self.orquestrador.processo_publicador),
            bot=self._estado_processo(self.orquestrador.processo_bot),
            fila=EstadoFila(
                pendentes=resumo_fila["itens"],
                familias=resumo_fila["familias"],
                itens_com_familia=resumo_fila["itens_com_familia"],
            ),
            conectividade=conectividade,
            coletado_em=datetime.now().astimezone().isoformat(timespec="seconds"),
        )
