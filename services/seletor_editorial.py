# 63.8738, -149.7525

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from repositories.fila_publicacao_repository import ItemFilaPublicacao

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ResultadoSelecaoEditorial:
    item: ItemFilaPublicacao
    prioridade_editorial: float
    motivos: tuple[str, ...]


class SeletorEditorial:
    """Escolhe o próximo post combinando qualidade, urgência e diversidade.

    Regras principais:
    - categoria recém-publicada entra em bloqueio temporário quando existe
      alternativa válida de outra categoria;
    - se não existir alternativa, a categoria pode repetir;
    - marca recente recebe penalidade forte;
    - categoria saturada na janela recente perde muita prioridade;
    - anomalias fortes validadas continuam podendo furar a ordem normal.
    """

    def __init__(
        self,
        cooldown_categoria_minutos: float = 12.0,
        cooldown_marca_minutos: float = 8.0,
        cooldown_canonico_minutos: float = 180.0,
        cooldown_familia_minutos: float = 720.0,
        queda_minima_repost_familia_percentual: float = 5.0,
        bloqueio_categoria_minutos: float = 8.0,
        janela_saturacao_categoria_minutos: float = 30.0,
        limite_categoria_janela: int = 2,
    ) -> None:
        self.cooldown_categoria_minutos = cooldown_categoria_minutos
        self.cooldown_marca_minutos = cooldown_marca_minutos
        self.cooldown_canonico_minutos = cooldown_canonico_minutos
        self.cooldown_familia_minutos = cooldown_familia_minutos
        self.queda_minima_repost_familia_percentual = queda_minima_repost_familia_percentual
        self.bloqueio_categoria_minutos = bloqueio_categoria_minutos
        self.janela_saturacao_categoria_minutos = janela_saturacao_categoria_minutos
        self.limite_categoria_janela = limite_categoria_janela

    def escolher(
        self,
        pendentes: list[ItemFilaPublicacao],
        historico_publicacoes: list[dict],
        agora: datetime | None = None,
    ) -> ResultadoSelecaoEditorial | None:
        if not pendentes:
            return None

        agora = agora or datetime.now().astimezone()

        pendentes = self._filtrar_familias_em_cooldown(
            pendentes=pendentes,
            historico_publicacoes=historico_publicacoes,
            agora=agora,
        )

        if not pendentes:
            return None

        candidatos = self._aplicar_bloqueio_categoria(
            pendentes=pendentes,
            historico_publicacoes=historico_publicacoes,
            agora=agora,
        )

        avaliados = [
            self._avaliar_item(
                item=item,
                historico_publicacoes=historico_publicacoes,
                agora=agora,
            )
            for item in candidatos
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

    def _filtrar_familias_em_cooldown(
        self,
        pendentes: list[ItemFilaPublicacao],
        historico_publicacoes: list[dict],
        agora: datetime,
    ) -> list[ItemFilaPublicacao]:
        liberados: list[ItemFilaPublicacao] = []

        for item in pendentes:
            chave = self._normalizar(item.oferta.chave_familia_produto)

            if not chave or item.oferta.confianca_familia < 80:
                liberados.append(item)
                continue

            ultimo = self._ultimo_registro(
                historico_publicacoes,
                campo="chave_familia",
                valor=chave,
            )

            if ultimo is None:
                liberados.append(item)
                continue

            publicado_em = ultimo.get("publicado_em")
            if not publicado_em:
                liberados.append(item)
                continue

            instante = datetime.fromisoformat(str(publicado_em))
            minutos = max(
                0.0,
                (agora - instante).total_seconds() / 60.0,
            )

            if minutos >= self.cooldown_familia_minutos:
                liberados.append(item)
                continue

            # Oportunidade anômala validada pode furar o cooldown.
            if item.oferta.tipo_oportunidade in {
                "possivel_preco_bugado",
                "anomalia_forte",
            }:
                logger.info(
                    (
                        "Anti-repost: família '%s' liberada antes do cooldown "
                        "por oportunidade anômala validada."
                    ),
                    item.oferta.familia_produto or item.oferta.chave_familia_produto,
                )
                liberados.append(item)
                continue

            preco_anterior = ultimo.get("preco")
            queda = 0.0

            if preco_anterior:
                preco_anterior = float(preco_anterior)
                if preco_anterior > 0 and item.oferta.preco < preco_anterior:
                    queda = (preco_anterior - item.oferta.preco) / preco_anterior * 100

            # Republicação só entra antes do cooldown se houver uma queda
            # material em relação ao representante da família já publicado.
            if (
                item.deve_republicar_por_queda
                and queda >= self.queda_minima_repost_familia_percentual
            ):
                logger.info(
                    (
                        "Anti-repost: família '%s' liberada antes do cooldown "
                        "por queda real de %.2f%% (mínimo %.2f%%)."
                    ),
                    item.oferta.familia_produto or item.oferta.chave_familia_produto,
                    queda,
                    self.queda_minima_repost_familia_percentual,
                )
                liberados.append(item)
                continue

            restante = max(
                0.0,
                self.cooldown_familia_minutos - minutos,
            )

            logger.info(
                (
                    "Anti-repost: bloqueando família '%s' por cooldown. "
                    "Publicado há %.1f min; faltam aproximadamente %.1f min. "
                    "Queda atual: %.2f%%."
                ),
                item.oferta.familia_produto or item.oferta.chave_familia_produto,
                minutos,
                restante,
                queda,
            )

        return liberados

    @staticmethod
    def _ultimo_registro(
        historico_publicacoes: list[dict],
        campo: str,
        valor: str,
    ) -> dict | None:
        valor_normalizado = SeletorEditorial._normalizar(valor)

        for registro in historico_publicacoes:
            if SeletorEditorial._normalizar(registro.get(campo)) == valor_normalizado:
                return registro

        return None

    def _aplicar_bloqueio_categoria(
        self,
        pendentes: list[ItemFilaPublicacao],
        historico_publicacoes: list[dict],
        agora: datetime,
    ) -> list[ItemFilaPublicacao]:
        """Evita repetição imediata quando há alternativa de outra categoria.

        O bloqueio é editorial, não absoluto: se toda a fila disponível for
        da mesma categoria, ela continua podendo publicar.
        """

        ultima_categoria, minutos_desde_ultima = self._ultima_categoria_publicada(
            historico_publicacoes=historico_publicacoes,
            agora=agora,
        )

        if (
            not ultima_categoria
            or minutos_desde_ultima is None
            or minutos_desde_ultima >= self.bloqueio_categoria_minutos
        ):
            return pendentes

        alternativas = [
            item
            for item in pendentes
            if self._normalizar(item.oferta.categoria) != ultima_categoria
            or item.oferta.tipo_oportunidade in {"possivel_preco_bugado", "anomalia_forte"}
        ]

        if not alternativas:
            return pendentes

        return alternativas

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
            penalidade = 24.0 * proporcao
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
            penalidade = 24.0 * proporcao
            prioridade -= penalidade
            motivos.append(f"marca recente: -{penalidade:.1f}")

        repeticoes_categoria = self._contar_recentes(
            historico_publicacoes=historico_publicacoes,
            campo="categoria",
            valor=item.oferta.categoria,
            agora=agora,
            janela_minutos=self.janela_saturacao_categoria_minutos,
        )

        if repeticoes_categoria >= self.limite_categoria_janela:
            excedente = repeticoes_categoria - self.limite_categoria_janela + 1
            penalidade = min(60.0, 28.0 + (excedente - 1) * 12.0)
            prioridade -= penalidade
            motivos.append(
                "categoria saturada " f"({repeticoes_categoria} recentes): -{penalidade:.1f}"
            )

        minutos_familia = self._minutos_desde_ultimo(
            historico_publicacoes,
            campo="chave_familia",
            valor=item.oferta.chave_familia_produto,
            agora=agora,
        )

        if minutos_familia is not None and minutos_familia < self.cooldown_familia_minutos:
            prioridade -= 60.0
            motivos.append("família publicada recentemente: -60")

        minutos_canonico = self._minutos_desde_ultimo(
            historico_publicacoes,
            campo="chave_canonica",
            valor=item.oferta.chave_produto_canonica,
            agora=agora,
        )

        if minutos_canonico is not None and minutos_canonico < self.cooldown_canonico_minutos:
            proporcao = 1 - (minutos_canonico / self.cooldown_canonico_minutos)
            penalidade = 45.0 * proporcao
            prioridade -= penalidade
            motivos.append(f"mesmo produto recente: -{penalidade:.1f}")

        return ResultadoSelecaoEditorial(
            item=item,
            prioridade_editorial=round(prioridade, 2),
            motivos=tuple(motivos),
        )

    def _ultima_categoria_publicada(
        self,
        historico_publicacoes: list[dict],
        agora: datetime,
    ) -> tuple[str | None, float | None]:
        for registro in historico_publicacoes:
            categoria = self._normalizar(registro.get("categoria"))

            if not categoria:
                continue

            publicado_em = registro.get("publicado_em")

            if not publicado_em:
                continue

            instante = datetime.fromisoformat(str(publicado_em))
            minutos = max(
                0.0,
                (agora - instante).total_seconds() / 60.0,
            )

            return categoria, minutos

        return None, None

    def _contar_recentes(
        self,
        historico_publicacoes: list[dict],
        campo: str,
        valor: str | None,
        agora: datetime,
        janela_minutos: float,
    ) -> int:
        valor_normalizado = self._normalizar(valor)

        if not valor_normalizado:
            return 0

        quantidade = 0

        for registro in historico_publicacoes:
            valor_registro = self._normalizar(registro.get(campo))

            if valor_registro != valor_normalizado:
                continue

            publicado_em = registro.get("publicado_em")

            if not publicado_em:
                continue

            instante = datetime.fromisoformat(str(publicado_em))
            minutos = max(
                0.0,
                (agora - instante).total_seconds() / 60.0,
            )

            if minutos <= janela_minutos:
                quantidade += 1

        return quantidade

    @staticmethod
    def _minutos_desde_ultimo(
        historico_publicacoes: list[dict],
        campo: str,
        valor: str | None,
        agora: datetime,
    ) -> float | None:
        valor_normalizado = SeletorEditorial._normalizar(valor)

        if not valor_normalizado:
            return None

        for registro in historico_publicacoes:
            valor_registro = SeletorEditorial._normalizar(registro.get(campo))

            if valor_registro != valor_normalizado:
                continue

            publicado_em = registro.get("publicado_em")

            if not publicado_em:
                continue

            instante = datetime.fromisoformat(str(publicado_em))
            diferenca = agora - instante

            return max(0.0, diferenca.total_seconds() / 60.0)

        return None

    @staticmethod
    def _normalizar(valor: object) -> str:
        if not isinstance(valor, str):
            return ""

        return valor.strip().casefold()
