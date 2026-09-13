from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from models.personalized_notification_outbox import (
    ItemOutboxNotificacaoPersonalizada,
)
from repositories.personalized_notification_outbox_repository import (
    PersonalizedNotificationOutboxRepository,
)

_MAX_ERRO = 500


class PersonalizedNotificationOutboxService:
    def __init__(
        self,
        repository: PersonalizedNotificationOutboxRepository,
    ) -> None:
        self.repository = repository

    @staticmethod
    def _agora_dt() -> datetime:
        return datetime.now(UTC)

    @classmethod
    def _agora(cls) -> str:
        return cls._agora_dt().isoformat()

    @staticmethod
    def _normalizar_erro(erro: str) -> str:
        valor = " ".join(erro.split()).strip()
        if not valor:
            raise ValueError("Erro de delivery nao pode ser vazio.")
        return valor[:_MAX_ERRO]

    def sincronizar_matches_pendentes(
        self,
        *,
        limite: int = 100,
    ) -> list[ItemOutboxNotificacaoPersonalizada]:
        fontes = self.repository.listar_matches_sem_outbox(
            limite=limite,
        )

        criados: list[ItemOutboxNotificacaoPersonalizada] = []

        for match_id, conta_id, canonical_key in fontes:
            agora = self._agora()

            item, criado = self.repository.enfileirar(
                outbox_id=f"pno_{uuid.uuid4().hex}",
                match_id=match_id,
                conta_id=conta_id,
                canonical_key=canonical_key,
                disponivel_em=agora,
                agora=agora,
            )

            if criado:
                criados.append(item)

        return criados

    def reservar_proximo(
        self,
    ) -> ItemOutboxNotificacaoPersonalizada | None:
        agora = self._agora()

        candidatos = self.repository.listar_disponiveis(
            agora=agora,
            limite=25,
        )

        for candidato in candidatos:
            if self.repository.reservar(
                outbox_id=candidato.id,
                agora=agora,
            ):
                reservado = self.repository.obter_por_id(candidato.id)
                if reservado is None:
                    raise RuntimeError("Item reservado desapareceu da outbox.")
                return reservado

        return None

    def registrar_sucesso(
        self,
        outbox_id: str,
    ) -> ItemOutboxNotificacaoPersonalizada:
        agora = self._agora()

        if not self.repository.marcar_entregue(
            outbox_id=outbox_id,
            agora=agora,
        ):
            raise ValueError("Somente item em processing pode ser entregue.")

        item = self.repository.obter_por_id(outbox_id)
        if item is None:
            raise RuntimeError("Item entregue desapareceu da outbox.")
        return item

    def registrar_retry(
        self,
        outbox_id: str,
        *,
        erro: str,
        atraso_segundos: int = 300,
    ) -> ItemOutboxNotificacaoPersonalizada:
        if atraso_segundos < 1:
            raise ValueError("Atraso de retry precisa ser positivo.")

        agora_dt = self._agora_dt()
        agora = agora_dt.isoformat()
        disponivel_em = (agora_dt + timedelta(seconds=atraso_segundos)).isoformat()

        if not self.repository.marcar_retry(
            outbox_id=outbox_id,
            disponivel_em=disponivel_em,
            erro=self._normalizar_erro(erro),
            agora=agora,
        ):
            raise ValueError("Somente item em processing pode voltar para retry.")

        item = self.repository.obter_por_id(outbox_id)
        if item is None:
            raise RuntimeError("Item de retry desapareceu da outbox.")
        return item

    def registrar_falha_terminal(
        self,
        outbox_id: str,
        *,
        erro: str,
    ) -> ItemOutboxNotificacaoPersonalizada:
        agora = self._agora()

        if not self.repository.marcar_falha_terminal(
            outbox_id=outbox_id,
            erro=self._normalizar_erro(erro),
            agora=agora,
        ):
            raise ValueError("Somente item em processing pode falhar terminalmente.")

        item = self.repository.obter_por_id(outbox_id)
        if item is None:
            raise RuntimeError("Item com falha desapareceu da outbox.")
        return item
