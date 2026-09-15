from __future__ import annotations

from decimal import Decimal

from models.personalized_notification_outbox import (
    ItemOutboxNotificacaoPersonalizada,
)
from models.push_dispatcher import ConteudoPushPersonalizado
from repositories.alert_engine_repository import AlertEngineRepository
from repositories.personalized_alert_match_repository import (
    PersonalizedAlertMatchRepository,
)


class PushPayloadBuilder:
    _MARKETPLACES = {
        "mercado_livre": "Mercado Livre",
        "shopee": "Shopee",
        "kabum": "KaBuM!",
        "aliexpress": "AliExpress",
    }

    def __init__(
        self,
        *,
        match_repository: PersonalizedAlertMatchRepository,
        alert_engine_repository: AlertEngineRepository,
    ) -> None:
        self.match_repository = match_repository
        self.alert_engine_repository = alert_engine_repository

    def montar(
        self,
        outbox: ItemOutboxNotificacaoPersonalizada,
    ) -> ConteudoPushPersonalizado:
        match = self.match_repository.obter_por_id(outbox.match_id)
        if match is None:
            raise ValueError("Match da outbox nao encontrado.")

        if match.conta_id != outbox.conta_id:
            raise ValueError("Match da outbox pertence a outra conta.")
        if match.canonical_key != outbox.canonical_key:
            raise ValueError("Match da outbox diverge da identidade canonica.")

        estado = self.alert_engine_repository.obter_estado_produto(
            match.canonical_key,
            limite_eventos=1,
        )
        if estado is None:
            raise ValueError("Produto canonico da notificacao nao encontrado.")

        produto = estado.get("produto")
        if not isinstance(produto, dict):
            raise ValueError("Estado canonico da notificacao invalido.")

        nome = str(produto.get("nome_canonico") or "").strip()
        if not nome:
            raise ValueError("Nome canonico da notificacao indisponivel.")

        titulo = self._titulo(match.motivos, match.tipo_evento)
        preco = self._formatar_brl(match.preco_atual)
        marketplace = self._marketplace(match.marketplace)
        corpo = f"{nome} por {preco} em {marketplace}."

        return ConteudoPushPersonalizado(
            titulo=titulo,
            corpo=corpo,
            dados={
                "type": "price_alert",
                "canonicalKey": match.canonical_key,
                "matchId": match.id,
                "outboxId": outbox.id,
                "marketplace": match.marketplace,
                "price": float(match.preco_atual),
            },
        )

    @staticmethod
    def _titulo(motivos: tuple[str, ...], tipo_evento: str) -> str:
        if "new_historical_low" in motivos:
            return "Novo menor preco"
        if "target_price_reached" in motivos:
            return "Preco-alvo atingido"
        if "price_drop_detected" in motivos:
            return "Preco caiu"
        if tipo_evento == "novo_menor_preco_historico":
            return "Novo menor preco"
        return "Oferta monitorada atualizada"

    @classmethod
    def _marketplace(cls, marketplace: str | None) -> str:
        chave = str(marketplace or "").strip().lower()
        if not chave:
            return "loja monitorada"
        return cls._MARKETPLACES.get(chave, chave.replace("_", " ").title())

    @staticmethod
    def _formatar_brl(valor: Decimal) -> str:
        numero = f"{float(valor):,.2f}"
        numero = numero.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {numero}"
