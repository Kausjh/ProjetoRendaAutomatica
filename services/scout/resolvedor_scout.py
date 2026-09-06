# 63.8738, -149.7525

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from models.resolucao_scout import ResolucaoScout
from models.sinal_scout import SinalScout
from repositories.resolucoes_scout_repository import (
    ResolucoesScoutRepository,
)
from repositories.sinais_scout_repository import (
    SinaisScoutRepository,
)

logger = logging.getLogger(__name__)


class ResolvedorSinalScout(Protocol):
    nome: str

    def suporta(
        self,
        sinal: SinalScout,
    ) -> bool: ...

    def resolver(
        self,
        sinal: SinalScout,
    ) -> ResolucaoScout: ...


@dataclass(
    frozen=True,
    slots=True,
)
class ResultadoResolvedorScout:
    sinais_lidos: int
    processados: int
    resolvidos: int
    landing_pages: int
    nao_suportados: int
    erros: int
    ignorados_existentes: int


class ResolvedorRadarScout:
    def __init__(
        self,
        resolvedores: list[ResolvedorSinalScout],
        sinais_repository: SinaisScoutRepository | None = None,
        resolucoes_repository: ResolucoesScoutRepository | None = None,
    ) -> None:
        self.resolvedores = resolvedores

        self.sinais_repository = sinais_repository or SinaisScoutRepository()

        self.resolucoes_repository = resolucoes_repository or ResolucoesScoutRepository()

    def executar(
        self,
        limite: int | None = None,
        reprocessar: bool = False,
    ) -> ResultadoResolvedorScout:
        sinais = self.sinais_repository.listar()

        limite_processamento = (
            None
            if limite is None
            else max(
                int(limite),
                0,
            )
        )

        processados = 0
        resolvidos = 0
        landing_pages = 0
        nao_suportados = 0
        erros = 0
        ignorados_existentes = 0

        for sinal in sinais:
            if limite_processamento is not None and processados >= limite_processamento:
                break

            existente = self.resolucoes_repository.obter(
                sinal.fonte,
                sinal.id_externo,
            )

            if existente is not None and not reprocessar:
                ignorados_existentes += 1
                continue

            resolvedor = next(
                (item for item in self.resolvedores if item.suporta(sinal)),
                None,
            )

            if resolvedor is None:
                resolucao = ResolucaoScout(
                    fonte=sinal.fonte,
                    id_externo=(sinal.id_externo),
                    status=("nao_suportado"),
                    motivo=("sem_resolvedor_" "para_fonte"),
                )

            else:
                try:
                    resolucao = resolvedor.resolver(sinal)

                except Exception as erro:
                    logger.exception(
                        ("Radar Scout: falha " "ao resolver sinal " "%s/%s."),
                        sinal.fonte,
                        sinal.id_externo,
                    )

                    resolucao = ResolucaoScout(
                        fonte=(sinal.fonte),
                        id_externo=(sinal.id_externo),
                        status="erro",
                        motivo=("falha_resolvedor:" + type(erro).__name__),
                    )

            self.resolucoes_repository.salvar(resolucao)

            processados += 1

            if resolucao.status == "resolvido":
                resolvidos += 1

            elif resolucao.status == "landing_page":
                landing_pages += 1

            elif resolucao.status == "nao_suportado":
                nao_suportados += 1

            elif resolucao.status == "erro":
                erros += 1

        return ResultadoResolvedorScout(
            sinais_lidos=len(sinais),
            processados=processados,
            resolvidos=resolvidos,
            landing_pages=(landing_pages),
            nao_suportados=(nao_suportados),
            erros=erros,
            ignorados_existentes=(ignorados_existentes),
        )
