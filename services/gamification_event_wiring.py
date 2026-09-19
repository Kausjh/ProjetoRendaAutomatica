from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from services.gamification_service import (
    ConflitoEventoGamificacao,
    GamificationService,
    LimiteGamificacaoExcedido,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResultadoWiringGamificacao:
    status: str
    evento_id: str | None


class GamificationEventWiring:
    def __init__(
        self,
        service: GamificationService,
    ) -> None:
        self.service = service

    def _registrar(
        self,
        *,
        conta_id: str,
        chave_idempotencia: str,
        tipo_evento: str,
        origem_id: str,
        ocorrido_em: datetime | None = None,
    ) -> ResultadoWiringGamificacao:
        try:
            resultado = self.service.registrar_evento(
                conta_id=conta_id,
                chave_idempotencia=(chave_idempotencia),
                tipo_evento=tipo_evento,
                origem="user_state_v1",
                origem_id=origem_id,
                ocorrido_em=ocorrido_em,
            )

            return ResultadoWiringGamificacao(
                status=("created" if resultado.criado else "idempotent"),
                evento_id=resultado.evento.id,
            )

        except LimiteGamificacaoExcedido:
            logger.info(
                "Evento de gamificacao limitado: " "conta=%s tipo=%s",
                conta_id,
                tipo_evento,
            )

            return ResultadoWiringGamificacao(
                status="limited",
                evento_id=None,
            )

        except ConflitoEventoGamificacao:
            logger.error(
                "Conflito de idempotencia " "na gamificacao: conta=%s tipo=%s",
                conta_id,
                tipo_evento,
            )

            return ResultadoWiringGamificacao(
                status="conflict",
                evento_id=None,
            )

        except Exception:
            logger.exception(
                "Falha nao bloqueante " "no wiring de gamificacao: " "conta=%s tipo=%s",
                conta_id,
                tipo_evento,
            )

            return ResultadoWiringGamificacao(
                status="error",
                evento_id=None,
            )

    def registrar_conta_criada(
        self,
        *,
        conta_id: str,
        ocorrido_em: datetime | None = None,
    ) -> ResultadoWiringGamificacao:
        return self._registrar(
            conta_id=conta_id,
            chave_idempotencia=("v1:onboarding_conta_criada"),
            tipo_evento=("onboarding_conta_criada"),
            origem_id=conta_id,
            ocorrido_em=ocorrido_em,
        )

    def registrar_primeiro_dispositivo(
        self,
        *,
        conta_id: str,
        ocorrido_em: datetime | None = None,
    ) -> ResultadoWiringGamificacao:
        return self._registrar(
            conta_id=conta_id,
            chave_idempotencia=("v1:onboarding_dispositivo_vinculado"),
            tipo_evento=("onboarding_dispositivo_vinculado"),
            origem_id=conta_id,
            ocorrido_em=ocorrido_em,
        )

    def registrar_preferencias_definidas(
        self,
        *,
        conta_id: str,
        ocorrido_em: datetime | None = None,
    ) -> ResultadoWiringGamificacao:
        return self._registrar(
            conta_id=conta_id,
            chave_idempotencia=("v1:onboarding_preferencias_definidas"),
            tipo_evento=("onboarding_preferencias_definidas"),
            origem_id=conta_id,
            ocorrido_em=ocorrido_em,
        )

    def registrar_produto_watchlist(
        self,
        *,
        conta_id: str,
        canonical_key: str,
        ocorrido_em: datetime | None = None,
    ) -> ResultadoWiringGamificacao:
        return self._registrar(
            conta_id=conta_id,
            chave_idempotencia=("v1:watchlist_produto_adicionado:" + canonical_key),
            tipo_evento=("watchlist_produto_adicionado"),
            origem_id=canonical_key,
            ocorrido_em=ocorrido_em,
        )

    def registrar_preco_alvo(
        self,
        *,
        conta_id: str,
        canonical_key: str,
        ocorrido_em: datetime | None = None,
    ) -> ResultadoWiringGamificacao:
        return self._registrar(
            conta_id=conta_id,
            chave_idempotencia=("v1:watchlist_preco_alvo_definido:" + canonical_key),
            tipo_evento=("watchlist_preco_alvo_definido"),
            origem_id=canonical_key,
            ocorrido_em=ocorrido_em,
        )
