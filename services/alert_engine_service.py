from __future__ import annotations

from math import isfinite

from models.alert_engine import ResultadoAlertEngine
from models.price_intelligence import ResultadoObservacaoPriceIntelligence
from repositories.alert_engine_repository import AlertEngineRepository
from repositories.price_intelligence_repository import (
    PriceIntelligenceRepository,
)


class AlertEngineService:
    def __init__(
        self,
        *,
        repository: AlertEngineRepository,
        price_intelligence_repository: PriceIntelligenceRepository,
    ) -> None:
        self.repository = repository
        self.price_intelligence_repository = price_intelligence_repository

    def processar(
        self,
        resultado_price_intelligence: ResultadoObservacaoPriceIntelligence,
    ) -> ResultadoAlertEngine:
        if not resultado_price_intelligence.registrado:
            return self._ignorado(
                "ignorado_price_intelligence_nao_registrado",
                "Price Intelligence nao confirmou observacao persistida.",
                resultado_price_intelligence,
            )

        if not resultado_price_intelligence.nova_observacao_historica:
            return self._ignorado(
                "ignorado_sem_nova_observacao_historica",
                "Nenhuma nova observacao historica foi criada.",
                resultado_price_intelligence,
            )

        chave = self._texto(resultado_price_intelligence.chave_canonica)
        marketplace = self._texto(resultado_price_intelligence.marketplace)
        identificador = self._texto(resultado_price_intelligence.identificador)
        preco = resultado_price_intelligence.preco

        if chave is None or marketplace is None or identificador is None or preco is None:
            return self._ignorado(
                "ignorado_identidade_ou_preco_insuficiente",
                "Identidade canonica, listing ou preco insuficiente.",
                resultado_price_intelligence,
            )

        try:
            preco_float = float(preco)
        except (TypeError, ValueError):
            return self._ignorado(
                "ignorado_preco_invalido",
                "Preco nao numerico.",
                resultado_price_intelligence,
            )

        if not isfinite(preco_float) or preco_float <= 0:
            return self._ignorado(
                "ignorado_preco_invalido",
                "Preco precisa ser finito e positivo.",
                resultado_price_intelligence,
            )

        snapshot = self.price_intelligence_repository.obter_snapshot(chave)
        if snapshot is None or snapshot.chave_canonica != chave:
            return self._ignorado(
                "ignorado_snapshot_indisponivel",
                "Snapshot canonico consistente indisponivel.",
                resultado_price_intelligence,
            )

        menor_historico = float(snapshot.menor_preco_historico)
        if not isfinite(menor_historico) or menor_historico <= 0:
            return self._ignorado(
                "ignorado_evidencia_historica_invalida",
                "Menor preco historico invalido.",
                resultado_price_intelligence,
            )

        persistido = self.repository.processar_observacao(
            chave_canonica=chave,
            nome_canonico=snapshot.nome_canonico,
            marketplace=marketplace,
            identificador=identificador,
            preco_atual=preco_float,
            menor_preco_historico=menor_historico,
        )

        if persistido["status"] == "conflito_identidade":
            return self._ignorado(
                "ignorado_conflito_identidade",
                "Listing associado a outra identidade canonica.",
                resultado_price_intelligence,
            )

        return ResultadoAlertEngine(
            status=str(persistido["status"]),
            processado=True,
            baseline_inicializada=bool(persistido["baseline_inicializada"]),
            alertas_gerados=int(persistido["alertas_gerados"]),
            tipos_gerados=tuple(persistido["tipos_gerados"]),
            chave_canonica=chave,
            marketplace=marketplace,
            identificador=identificador,
            motivo="Observacao canonica processada pelo Alert Engine.",
        )

    @staticmethod
    def _texto(valor: object) -> str | None:
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto or None

    @staticmethod
    def _ignorado(
        status: str,
        motivo: str,
        resultado: ResultadoObservacaoPriceIntelligence,
    ) -> ResultadoAlertEngine:
        return ResultadoAlertEngine(
            status=status,
            processado=False,
            baseline_inicializada=False,
            alertas_gerados=0,
            tipos_gerados=(),
            chave_canonica=resultado.chave_canonica,
            marketplace=resultado.marketplace,
            identificador=resultado.identificador,
            motivo=motivo,
        )
