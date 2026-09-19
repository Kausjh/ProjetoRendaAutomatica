from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from models.user_personalization import (
    ItemWatchlistUsuario,
    PreferenciasUsuario,
)
from repositories.user_identity_repository import UserIdentityRepository
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)
from services.gamification_event_wiring import GamificationEventWiring

_MARKETPLACE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,49}$")
_MAX_MARKETPLACES = 20
_MAX_CANONICAL_KEY = 200
_CENTAVOS = Decimal("0.01")


class UserPersonalizationService:
    def __init__(
        self,
        repository: UserPersonalizationRepository,
        identity_repository: UserIdentityRepository,
    ) -> None:
        self.repository = repository
        self.identity_repository = identity_repository

    @staticmethod
    def _agora() -> str:
        return datetime.now(UTC).isoformat()

    def _validar_conta_ativa(self, conta_id: str) -> None:
        conta = self.identity_repository.obter_conta(conta_id)
        if conta is None or not conta.ativa:
            raise ValueError("Conta inexistente ou inativa.")

    @staticmethod
    def _normalizar_marketplaces(
        marketplaces: list[str] | tuple[str, ...],
    ) -> tuple[str, ...]:
        normalizados: list[str] = []

        for marketplace in marketplaces:
            valor = marketplace.strip().lower()
            if not _MARKETPLACE_RE.fullmatch(valor):
                raise ValueError("Marketplace invalido.")
            if valor not in normalizados:
                normalizados.append(valor)

        if len(normalizados) > _MAX_MARKETPLACES:
            raise ValueError("Quantidade de marketplaces excede o limite.")

        return tuple(sorted(normalizados))

    @staticmethod
    def _normalizar_canonical_key(canonical_key: str) -> str:
        valor = canonical_key.strip()
        if not valor or len(valor) > _MAX_CANONICAL_KEY:
            raise ValueError("canonical_key invalida.")
        return valor

    @staticmethod
    def _preco_para_centavos(
        preco_alvo: Decimal | str | int | float | None,
    ) -> int | None:
        if preco_alvo is None:
            return None

        try:
            valor = Decimal(str(preco_alvo)).quantize(
                _CENTAVOS,
                rounding=ROUND_HALF_UP,
            )
        except (InvalidOperation, ValueError) as erro:
            raise ValueError("Preco alvo invalido.") from erro

        if not valor.is_finite() or valor <= 0:
            raise ValueError("Preco alvo precisa ser positivo.")

        return int(valor * 100)

    def configurar_gamificacao(
        self,
        gamification_event_wiring: GamificationEventWiring | None,
    ) -> None:
        self._gamification_event_wiring = gamification_event_wiring

    def obter_preferencias(
        self,
        conta_id: str,
    ) -> PreferenciasUsuario:
        self._validar_conta_ativa(conta_id)

        existentes = self.repository.obter_preferencias(conta_id)
        if existentes is not None:
            return existentes

        return self.repository.salvar_preferencias(
            conta_id=conta_id,
            notificacoes_preco_habilitadas=True,
            marketplaces_preferidos=(),
            atualizado_em=self._agora(),
        )

    def atualizar_preferencias(
        self,
        *,
        conta_id: str,
        notificacoes_preco_habilitadas: bool,
        marketplaces_preferidos: list[str] | tuple[str, ...],
    ) -> PreferenciasUsuario:
        self._validar_conta_ativa(conta_id)

        existentes = self.repository.obter_preferencias(conta_id)

        preferencias = self.repository.salvar_preferencias(
            conta_id=conta_id,
            notificacoes_preco_habilitadas=bool(notificacoes_preco_habilitadas),
            marketplaces_preferidos=(self._normalizar_marketplaces(marketplaces_preferidos)),
            atualizado_em=self._agora(),
        )

        wiring = getattr(
            self,
            "_gamification_event_wiring",
            None,
        )

        if wiring is not None and existentes is None:
            wiring.registrar_preferencias_definidas(
                conta_id=conta_id,
            )

        return preferencias

    def adicionar_ou_atualizar_watchlist(
        self,
        *,
        conta_id: str,
        canonical_key: str,
        preco_alvo: Decimal | str | int | float | None = None,
        notificar_queda_preco: bool = True,
    ) -> ItemWatchlistUsuario:
        self._validar_conta_ativa(conta_id)

        chave = self._normalizar_canonical_key(canonical_key)

        centavos = self._preco_para_centavos(preco_alvo)

        agora = self._agora()

        existente = self.repository.obter_item_watchlist(
            conta_id=conta_id,
            canonical_key=chave,
        )

        item = self.repository.salvar_item_watchlist(
            item_id=(existente.id if existente is not None else f"wat_{uuid.uuid4().hex}"),
            conta_id=conta_id,
            canonical_key=chave,
            preco_alvo_centavos=(centavos),
            notificar_queda_preco=bool(notificar_queda_preco),
            criado_em=(existente.criado_em if existente is not None else agora),
            atualizado_em=agora,
        )

        wiring = getattr(
            self,
            "_gamification_event_wiring",
            None,
        )

        if wiring is not None:
            if existente is None:
                wiring.registrar_produto_watchlist(
                    conta_id=conta_id,
                    canonical_key=chave,
                )

            preco_alvo_novo = centavos is not None and (
                existente is None or existente.preco_alvo is None
            )

            if preco_alvo_novo:
                wiring.registrar_preco_alvo(
                    conta_id=conta_id,
                    canonical_key=chave,
                )

        return item

    def listar_watchlist(
        self,
        conta_id: str,
    ) -> list[ItemWatchlistUsuario]:
        self._validar_conta_ativa(conta_id)
        return self.repository.listar_watchlist(conta_id)

    def remover_watchlist(
        self,
        *,
        conta_id: str,
        canonical_key: str,
    ) -> bool:
        self._validar_conta_ativa(conta_id)
        chave = self._normalizar_canonical_key(canonical_key)
        return self.repository.remover_item_watchlist(
            conta_id=conta_id,
            canonical_key=chave,
        )
