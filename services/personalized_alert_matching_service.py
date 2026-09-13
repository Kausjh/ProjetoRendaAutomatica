from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from models.personalized_alert_match import (
    CorrespondenciaAlertaPersonalizado,
    EventoAlertaPersonalizavel,
)
from repositories.personalized_alert_match_repository import (
    PersonalizedAlertMatchRepository,
)
from repositories.user_personalization_repository import (
    UserPersonalizationRepository,
)

_TIPOS_SUPORTADOS = {
    "mudanca_preco",
    "novo_menor_preco_historico",
}
_CENTAVOS = Decimal("0.01")


class PersonalizedAlertMatchingService:
    def __init__(
        self,
        *,
        personalization_repository: UserPersonalizationRepository,
        match_repository: PersonalizedAlertMatchRepository,
    ) -> None:
        self.personalization_repository = personalization_repository
        self.match_repository = match_repository

    @staticmethod
    def _agora() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _centavos(valor: Decimal) -> int:
        try:
            normalizado = Decimal(valor).quantize(
                _CENTAVOS,
                rounding=ROUND_HALF_UP,
            )
        except (InvalidOperation, ValueError) as erro:
            raise ValueError("Preco de evento invalido.") from erro

        if not normalizado.is_finite() or normalizado <= 0:
            raise ValueError("Preco de evento precisa ser positivo.")

        return int(normalizado * 100)

    @staticmethod
    def _normalizar_marketplace(
        marketplace: str | None,
    ) -> str | None:
        if marketplace is None:
            return None

        valor = marketplace.strip().lower()
        return valor or None

    @staticmethod
    def _evento_e_queda(
        evento: EventoAlertaPersonalizavel,
    ) -> bool:
        if evento.tipo_evento == "novo_menor_preco_historico":
            return True

        if evento.tipo_evento != "mudanca_preco":
            return False

        if evento.preco_anterior is None:
            return False

        return evento.preco_atual < evento.preco_anterior

    def processar_evento(
        self,
        evento: EventoAlertaPersonalizavel,
    ) -> list[CorrespondenciaAlertaPersonalizado]:
        if not evento.evento_id.strip():
            raise ValueError("evento_id obrigatorio.")

        canonical_key = evento.canonical_key.strip()
        if not canonical_key:
            raise ValueError("canonical_key obrigatoria.")

        if evento.tipo_evento not in _TIPOS_SUPORTADOS:
            return []

        preco_atual_centavos = self._centavos(evento.preco_atual)
        marketplace = self._normalizar_marketplace(evento.marketplace)

        itens = self.personalization_repository.listar_watchlists_por_canonical_key(canonical_key)

        correspondencias: list[CorrespondenciaAlertaPersonalizado] = []

        for item in itens:
            preferencias = self.personalization_repository.obter_preferencias(item.conta_id)

            if preferencias is not None and not preferencias.notificacoes_preco_habilitadas:
                continue

            if preferencias is not None and preferencias.marketplaces_preferidos:
                if marketplace is None or marketplace not in preferencias.marketplaces_preferidos:
                    continue

            motivos: list[str] = []

            if item.preco_alvo is not None and evento.preco_atual <= item.preco_alvo:
                motivos.append("target_price_reached")

            if item.notificar_queda_preco and self._evento_e_queda(evento):
                if evento.tipo_evento == "novo_menor_preco_historico":
                    motivos.append("new_historical_low")
                else:
                    motivos.append("price_drop_detected")

            if not motivos:
                continue

            match, _ = self.match_repository.salvar_correspondencia(
                match_id=f"pam_{uuid.uuid4().hex}",
                evento_alerta_id=evento.evento_id.strip(),
                watchlist_id=item.id,
                conta_id=item.conta_id,
                canonical_key=canonical_key,
                tipo_evento=evento.tipo_evento,
                preco_atual_centavos=preco_atual_centavos,
                marketplace=marketplace,
                motivos=tuple(motivos),
                criado_em=self._agora(),
            )

            correspondencias.append(match)

        return correspondencias
