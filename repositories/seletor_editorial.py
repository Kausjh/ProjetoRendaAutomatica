# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from repositories.fila_publicacao_repository import ItemFilaPublicacao


@dataclass(frozen=True, slots=True)
class ResultadoSelecaoEditorial:
    item: ItemFilaPublicacao
    prioridade_editorial: float
    motivos: tuple[str, ...]


class SeletorEditorial:
    """Escolhe o próximo post considerando qualidade + diversidade.

    Cooldowns são penalidades, não bloqueios absolutos. Assim uma categoria
    pode repetir quando realmente não existe alternativa melhor.
    """

    def __init__(
        self,
        cooldown_categoria_minutos: float = 12.0,
        cooldown_marca_minutos: float = 8.0,
        cooldown_canonico_minutos: float = 180.0,
    ) -> None:
        self.cooldown_categoria_minutos = cooldown_categoria_minutos
        self.cooldown_marca_minutos = cooldown_marca_minutos
        self.cooldown_canonico_minutos = cooldown_canonico_minutos

    def escolher(
        self,
        pendentes: list[ItemFilaPublicacao],
        historico_publicacoes: list[dict],
        agora: datetime | None = None,
    ) -> ResultadoSelecaoEditorial | None:
        if not pendentes:
            return None

        agora = agora or datetime.now().astimezone()

        avaliados = [
            self._avaliar_item(
                item=item,
                historico_publicacoes=historico_publicacoes,
                agora=agora,
            )
            for item in pendentes
        ]

        avaliados.sort(
            key=lambda resultado: (
                resultado.prioridade_editorial,
                resultado.item.prioridade,
                -resultado.item.id,
            ),
            reverse=True,
        )

        return avaliados[0]

    def _avaliar_item(
        self,
        item: ItemFilaPublicacao,
        historico_publicacoes: list[dict],
        agora: datetime,
    ) -> ResultadoSelecaoEditorial:
        prioridade = float(item.prioridade)
        motivos: list[str] = []

        if item.oferta.tipo_oportunidade == "possivel_preco_bugado":
            prioridade += 45.0
            motivos.append("possível preço bugado: +45")

        elif item.oferta.tipo_oportunidade == "anomalia_forte":
            prioridade += 30.0
            motivos.append("anomalia forte: +30")

        if item.deve_republicar_por_queda:
            prioridade += 8.0
            motivos.append("queda de preço confirmada: +8")

        minutos_categoria = self._minutos_desde_ultimo(
            historico_publicacoes,
            campo="categoria",
            valor=item.oferta.categoria,
            agora=agora,
        )

        if minutos_categoria is not None and minutos_categoria < self.cooldown_categoria_minutos:
            proporcao = 1 - (minutos_categoria / self.cooldown_categoria_minutos)
            penalidade = 22.0 * proporcao
            prioridade -= penalidade
            motivos.append(f"categoria recente: -{penalidade:.1f}")

        minutos_marca = self._minutos_desde_ultimo(
            historico_publicacoes,
            campo="marca",
            valor=item.oferta.marca,
            agora=agora,
        )

        if minutos_marca is not None and minutos_marca < self.cooldown_marca_minutos:
            proporcao = 1 - (minutos_marca / self.cooldown_marca_minutos)
            penalidade = 10.0 * proporcao
            prioridade -= penalidade
            motivos.append(f"marca recente: -{penalidade:.1f}")

        minutos_canonico = self._minutos_desde_ultimo(
            historico_publicacoes,
            campo="chave_canonica",
            valor=item.oferta.chave_produto_canonica,
            agora=agora,
        )

        if minutos_canonico is not None and minutos_canonico < self.cooldown_canonico_minutos:
            proporcao = 1 - (minutos_canonico / self.cooldown_canonico_minutos)
            penalidade = 35.0 * proporcao
            prioridade -= penalidade
            motivos.append(f"mesmo produto recente: -{penalidade:.1f}")

        return ResultadoSelecaoEditorial(
            item=item,
            prioridade_editorial=round(prioridade, 2),
            motivos=tuple(motivos),
        )

    @staticmethod
    def _minutos_desde_ultimo(
        historico_publicacoes: list[dict],
        campo: str,
        valor: str | None,
        agora: datetime,
    ) -> float | None:
        if not valor:
            return None

        valor_normalizado = valor.strip().casefold()

        for registro in historico_publicacoes:
            valor_registro = registro.get(campo)

            if not isinstance(valor_registro, str):
                continue

            if valor_registro.strip().casefold() != valor_normalizado:
                continue

            publicado_em = registro.get("publicado_em")

            if not publicado_em:
                continue

            instante = datetime.fromisoformat(str(publicado_em))
            diferenca = agora - instante

            return max(0.0, diferenca.total_seconds() / 60.0)

        return None
