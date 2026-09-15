# 63.8738, -149.7525

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from models.community_discovery import DescobertaComunitaria
from repositories.community_discovery_repository import (
    CommunityDiscoveryRepository,
)


class CommunityDiscoveryQueueService:
    def __init__(
        self,
        repository: CommunityDiscoveryRepository,
        *,
        max_tentativas: int = 5,
        atraso_base_segundos: int = 60,
        atraso_max_segundos: int = 3600,
        timeout_processamento_segundos: int = 900,
        agora_provider: Callable[[], datetime] | None = None,
    ) -> None:
        if max_tentativas < 1:
            raise ValueError("max_tentativas precisa ser positivo.")
        if atraso_base_segundos < 1:
            raise ValueError("atraso_base_segundos precisa ser positivo.")
        if atraso_max_segundos < atraso_base_segundos:
            raise ValueError("atraso_max_segundos nao pode ser menor que o atraso base.")
        if timeout_processamento_segundos < 1:
            raise ValueError("timeout_processamento_segundos precisa ser positivo.")

        self.repository = repository
        self.max_tentativas = int(max_tentativas)
        self.atraso_base_segundos = int(atraso_base_segundos)
        self.atraso_max_segundos = int(atraso_max_segundos)
        self.timeout_processamento_segundos = int(timeout_processamento_segundos)
        self.agora_provider = agora_provider or (lambda: datetime.now(UTC))

    def _agora(self) -> datetime:
        agora = self.agora_provider()

        if agora.tzinfo is None:
            return agora.replace(tzinfo=UTC)

        return agora.astimezone(UTC)

    @staticmethod
    def _motivo(valor: object) -> str:
        texto = " ".join(str(valor or "").split()).strip()

        if not texto:
            return "erro_processamento"

        return texto[:500]

    def reservar(
        self,
        *,
        limite: int = 10,
    ) -> list[DescobertaComunitaria]:
        agora = self._agora()
        agora_iso = agora.isoformat()

        processando_antes = (
            agora - timedelta(seconds=self.timeout_processamento_segundos)
        ).isoformat()

        self.repository.recuperar_processamentos_expirados(
            processando_antes=processando_antes,
            disponivel_em=agora_iso,
            agora=agora_iso,
        )

        return self.repository.reservar_pendentes(
            disponivel_ate=agora_iso,
            agora=agora_iso,
            limite=limite,
        )

    def aprovar(
        self,
        descoberta_id: str,
        *,
        canonical_key: str | None = None,
        motivo: str | None = None,
    ) -> DescobertaComunitaria:
        agora = self._agora().isoformat()

        if not self.repository.marcar_aprovada(
            descoberta_id,
            canonical_key=canonical_key,
            motivo=motivo,
            agora=agora,
        ):
            raise ValueError("Somente descoberta em processing pode ser aprovada.")

        return self._obter_obrigatoria(descoberta_id)

    def rejeitar(
        self,
        descoberta_id: str,
        *,
        motivo: str,
    ) -> DescobertaComunitaria:
        agora = self._agora().isoformat()

        if not self.repository.marcar_rejeitada(
            descoberta_id,
            motivo=self._motivo(motivo),
            agora=agora,
        ):
            raise ValueError("Somente descoberta em processing pode ser rejeitada.")

        return self._obter_obrigatoria(descoberta_id)

    def registrar_erro(
        self,
        descoberta_id: str,
        *,
        erro: object,
        transitorio: bool = True,
    ) -> DescobertaComunitaria:
        item = self._obter_obrigatoria(descoberta_id)

        if item.status != "processing":
            raise ValueError("Somente descoberta em processing pode registrar erro.")

        motivo = self._motivo(erro)
        agora_dt = self._agora()
        agora = agora_dt.isoformat()

        if transitorio and item.tentativas < self.max_tentativas:
            expoente = max(0, item.tentativas - 1)
            atraso = min(
                self.atraso_base_segundos * (2**expoente),
                self.atraso_max_segundos,
            )
            disponivel_em = (agora_dt + timedelta(seconds=atraso)).isoformat()

            if not self.repository.marcar_retry(
                descoberta_id,
                disponivel_em=disponivel_em,
                motivo=motivo,
                agora=agora,
            ):
                raise RuntimeError("Falha ao devolver descoberta para retry.")

            return self._obter_obrigatoria(descoberta_id)

        motivo_terminal = f"limite_tentativas:{motivo}" if transitorio else motivo

        if not self.repository.marcar_rejeitada(
            descoberta_id,
            motivo=motivo_terminal,
            agora=agora,
        ):
            raise RuntimeError("Falha ao rejeitar descoberta apos erro.")

        return self._obter_obrigatoria(descoberta_id)

    def _obter_obrigatoria(
        self,
        descoberta_id: str,
    ) -> DescobertaComunitaria:
        item = self.repository.obter_por_id(descoberta_id)

        if item is None:
            raise ValueError("Descoberta comunitaria nao encontrada.")

        return item
