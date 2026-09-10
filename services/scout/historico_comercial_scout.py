# 63.8738, -149.7525

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from models.perfil_comercial_scout import (
    PerfilComercialScout,
)
from models.tendencia_comercial_scout import (
    ObservacaoComercialScout,
)
from repositories.historico_comercial_scout_repository import (
    HistoricoComercialScoutRepository,
)


class HistoricoComercialScout:
    """
    Registra somente mudancas comerciais reais observadas.

    Eventos aceitos:
    - novo;
    - atualizado.

    Sinal inalterado nao gera nova observacao.
    """

    EVENTO_NOVO = "novo"
    EVENTO_ATUALIZADO = "atualizado"
    EVENTO_INALTERADO = "inalterado"

    EVENTOS_PERSISTIDOS = frozenset(
        {
            EVENTO_NOVO,
            EVENTO_ATUALIZADO,
        }
    )

    def __init__(
        self,
        repository: HistoricoComercialScoutRepository | None = None,
    ) -> None:
        self.repository = repository or HistoricoComercialScoutRepository()

    def registrar(
        self,
        *,
        perfil: PerfilComercialScout,
        tipo_evento: str,
        observado_em: datetime | None = None,
    ) -> bool:
        evento = str(tipo_evento or "").strip().casefold()

        if evento == self.EVENTO_INALTERADO:
            return False

        if evento not in self.EVENTOS_PERSISTIDOS:
            raise ValueError("tipo_evento comercial invalido.")

        if observado_em is None:
            observado_em = datetime.now(UTC)

        self.repository.registrar(
            perfil=perfil,
            tipo_evento=evento,
            observado_em=observado_em,
        )

        return True

    def observacoes_recentes(
        self,
        *,
        janela_horas: int,
        agora: datetime | None = None,
    ) -> list[ObservacaoComercialScout]:
        janela_horas = int(janela_horas)

        if janela_horas <= 0:
            raise ValueError("janela_horas deve ser maior que zero.")

        if agora is None:
            agora = datetime.now(UTC)

        agora = self._normalizar_data(agora)

        inicio = agora - timedelta(hours=janela_horas)

        return self.repository.listar_observacoes(
            inicio=inicio,
            fim=agora,
        )

    @staticmethod
    def _normalizar_data(
        valor: datetime,
    ) -> datetime:
        if not isinstance(
            valor,
            datetime,
        ):
            raise TypeError("agora deve ser datetime.")

        if valor.tzinfo is None or valor.utcoffset() is None:
            raise ValueError("agora deve possuir timezone.")

        return valor.astimezone(UTC)
