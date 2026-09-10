# 63.8738, -149.7525

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from models.estado_node import EstadoNode
from services.infra.node_data_quality import (
    analisar_qualidade_dados_node,
    salvar_qualidade_dados_node,
)
from services.infra.node_evidence_summary import (
    gerar_resumo_evidencias_node,
    salvar_resumo_evidencias_node,
)
from services.infra.node_health import (
    CAMINHO_ESTADO_PADRAO,
    DIRETORIO_PROJETO,
    capturar_estado_node,
    salvar_estado_node,
)
from services.infra.node_history_analysis import (
    analisar_historico_node,
    salvar_analise_node,
)
from services.infra.node_identity import (
    obter_ou_criar_node_id,
)
from services.infra.node_signal_analysis import (
    analisar_sinais_node,
    salvar_sinais_node,
)
from services.infra.node_signal_history_analysis import (
    analisar_historico_sinais_node,
    salvar_analise_historico_sinais_node,
)
from services.infra.node_signal_state import (
    persistir_estado_temporal_sinais,
)
from services.infra.node_temporal_evidence_quality import (
    analisar_qualidade_temporal_evidencia_node,
    salvar_qualidade_temporal_evidencia_node,
)
from services.infra.node_trend_analysis import (
    analisar_tendencia_node,
    salvar_tendencia_node,
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
        caminho_analise: str | Path | None = None,
        caminho_tendencia: str | Path | None = None,
        caminho_qualidade: str | Path | None = None,
        caminho_sinais: str | Path | None = None,
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
        analisar_historico: Callable[
            ...,
            object,
        ] = analisar_historico_node,
        salvar_analise: Callable[
            ...,
            Path,
        ] = salvar_analise_node,
        analisar_tendencia: Callable[
            ...,
            object,
        ] = analisar_tendencia_node,
        salvar_tendencia: Callable[
            ...,
            Path,
        ] = salvar_tendencia_node,
        analisar_qualidade: Callable[
            ...,
            object,
        ] = analisar_qualidade_dados_node,
        salvar_qualidade: Callable[
            ...,
            Path,
        ] = salvar_qualidade_dados_node,
        analisar_sinais: Callable[
            ...,
            object,
        ] = analisar_sinais_node,
        salvar_sinais: Callable[
            ...,
            Path,
        ] = salvar_sinais_node,
        persistir_estado_sinais: Callable[
            ...,
            object,
        ] = persistir_estado_temporal_sinais,
    ) -> None:
        intervalo_segundos = float(intervalo_segundos)

        if intervalo_segundos <= 0:
            raise ValueError("intervalo_segundos precisa " "ser maior que zero.")

        self.intervalo_segundos = intervalo_segundos

        self.caminho_estado = Path(caminho_estado)

        self.diretorio_historico = Path(diretorio_historico)

        diretorio_derivados = self.caminho_estado.parent

        self.caminho_analise = Path(
            caminho_analise
            if caminho_analise is not None
            else (diretorio_derivados / "analise_atual.json")
        )

        self.caminho_tendencia = Path(
            caminho_tendencia
            if caminho_tendencia is not None
            else (diretorio_derivados / "tendencia_atual.json")
        )

        self.caminho_qualidade = Path(
            caminho_qualidade
            if caminho_qualidade is not None
            else (diretorio_derivados / "qualidade_atual.json")
        )

        self.caminho_sinais = Path(
            caminho_sinais
            if caminho_sinais is not None
            else (diretorio_derivados / "sinais_atual.json")
        )

        self._obter_node_id = obter_node_id

        self._capturar_estado = capturar_estado

        self._salvar_estado = salvar_estado

        self._analisar_historico = analisar_historico

        self._salvar_analise = salvar_analise

        self._analisar_tendencia = analisar_tendencia

        self._salvar_tendencia = salvar_tendencia

        self._analisar_qualidade = analisar_qualidade

        self._salvar_qualidade = salvar_qualidade

        self._analisar_sinais = analisar_sinais

        self._salvar_sinais = salvar_sinais

        self._persistir_estado_sinais = persistir_estado_sinais

        self.caminho_estado_temporal_sinais = diretorio_derivados / "sinais_estado_atual.json"

        self.diretorio_historico_sinais = diretorio_derivados / "historico_sinais"

        self._parada = threading.Event()

    def solicitar_parada(
        self,
    ) -> None:
        self._parada.set()

    def executar_ciclo(
        self,
    ) -> EstadoNode:
        node_id = self._obter_node_id()

        estado = self._capturar_estado(node_id=node_id)

        self._salvar_estado(
            estado,
            self.caminho_estado,
        )

        self._registrar_historico(estado)

        self._atualizar_derivados()

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

    def _atualizar_derivados(
        self,
    ) -> None:
        tendencia_atualizada = False
        qualidade_atualizada = False

        try:
            analise = self._analisar_historico(self.diretorio_historico)

            self._salvar_analise(
                analise,
                self.caminho_analise,
            )

        except Exception:
            logger.exception("Falha ao atualizar " "analise historica " "do Node Health.")

        try:
            tendencia = self._analisar_tendencia(self.diretorio_historico)

            self._salvar_tendencia(
                tendencia,
                self.caminho_tendencia,
            )

            tendencia_atualizada = True

        except Exception:
            logger.exception("Falha ao atualizar " "tendencia " "do Node Health.")

        try:
            qualidade = self._analisar_qualidade(
                self.diretorio_historico,
                cadencia_nominal_segundos=(self.intervalo_segundos),
            )

            self._salvar_qualidade(
                qualidade,
                self.caminho_qualidade,
            )

            qualidade_atualizada = True

        except Exception:
            logger.exception("Falha ao atualizar " "qualidade dos dados " "do Node Health.")

        self._atualizar_sinais(
            tendencia_atualizada=(tendencia_atualizada),
            qualidade_atualizada=(qualidade_atualizada),
        )

    def _atualizar_sinais(
        self,
        *,
        tendencia_atualizada: bool,
        qualidade_atualizada: bool,
    ) -> None:
        if not (tendencia_atualizada and qualidade_atualizada):
            logger.warning(
                "Sinais do Node Health nao foram "
                "atualizados neste ciclo porque "
                "tendencia ou qualidade nao foi "
                "atualizada."
            )

            return

        try:
            sinais = self._analisar_sinais(
                self.caminho_estado,
                self.caminho_tendencia,
                self.caminho_qualidade,
                self.diretorio_historico,
            )

            self._salvar_sinais(
                sinais,
                self.caminho_sinais,
            )

            self._atualizar_estado_temporal_sinais(sinais)

        except Exception:
            logger.exception("Falha ao atualizar " "sinais observacionais " "do Node Health.")

    def _atualizar_estado_temporal_sinais(
        self,
        sinais: object,
    ) -> None:
        try:
            self._persistir_estado_sinais(
                sinais,
                caminho_estado=(self.caminho_estado_temporal_sinais),
                diretorio_historico=(self.diretorio_historico_sinais),
            )

        except Exception:
            logger.exception(
                "Falha ao atualizar persistencia " "temporal dos sinais do Node Health."
            )

            return

        self._atualizar_analise_historico_sinais()

    def _atualizar_analise_historico_sinais(
        self,
    ) -> None:
        caminho_analise = self.caminho_estado.parent / "analise_historico_sinais_atual.json"

        try:
            analise = analisar_historico_sinais_node(self.diretorio_historico_sinais)

            salvar_analise_historico_sinais_node(
                analise,
                caminho_analise,
            )

        except Exception:
            logger.exception("Falha ao atualizar analise historica " "dos sinais do Node Health.")

            return

        self._atualizar_resumo_evidencias(caminho_analise)

    def _atualizar_resumo_evidencias(
        self,
        caminho_analise_historica: Path,
    ) -> None:
        caminho_resumo = self.caminho_estado.parent / "resumo_evidencias_atual.json"

        try:
            resumo = gerar_resumo_evidencias_node(
                caminho_sinais=self.caminho_sinais,
                caminho_estado_temporal=(self.caminho_estado_temporal_sinais),
                caminho_historico_sinais=(caminho_analise_historica),
                caminho_qualidade=self.caminho_qualidade,
            )

            salvar_resumo_evidencias_node(
                resumo,
                caminho_resumo,
            )

        except Exception:
            logger.exception(
                "Falha ao atualizar resumo observacional " "de evidencias do Node Health."
            )

            return

        self._atualizar_qualidade_temporal_evidencia(
            caminho_resumo,
            caminho_analise_historica,
        )

    def _atualizar_qualidade_temporal_evidencia(
        self,
        caminho_resumo: Path,
        caminho_analise_historica: Path,
    ) -> None:
        try:
            analise = analisar_qualidade_temporal_evidencia_node(
                caminho_resumo=caminho_resumo,
                caminho_historico_sinais=(caminho_analise_historica),
            )

            salvar_qualidade_temporal_evidencia_node(
                analise,
                (self.caminho_estado.parent / "qualidade_evidencia_temporal_atual.json"),
            )

        except Exception:
            logger.exception(
                "Falha ao atualizar qualidade temporal " "da evidencia do Node Health."
            )

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
