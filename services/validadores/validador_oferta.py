# 63.8738, -149.7525

import logging
from dataclasses import dataclass
from urllib.parse import urlparse

from models.oferta import Oferta


logger = logging.getLogger(__name__)


@dataclass
class EstatisticasValidacao:
    """
    Consolida os resultados de uma etapa completa de validação.
    """

    ofertas_recebidas: int = 0
    ofertas_validas: int = 0
    ofertas_invalidas: int = 0

    nomes_vazios: int = 0
    links_invalidos: int = 0
    precos_invalidos: int = 0

    precos_antigos_removidos: int = 0
    descontos_divergentes: int = 0
    descontos_fora_intervalo: int = 0
    descontos_acima_limite: int = 0

    def formatar_resumo(self) -> str:
        """
        Retorna um resumo legível para registro no log.
        """

        separador = "-" * 46

        return "\n".join(
            [
                "Validação concluída:",
                separador,
                f"Ofertas recebidas: {self.ofertas_recebidas}",
                f"Ofertas válidas: {self.ofertas_validas}",
                f"Ofertas inválidas: {self.ofertas_invalidas}",
                separador,
                f"Nomes vazios: {self.nomes_vazios}",
                f"Links inválidos: {self.links_invalidos}",
                f"Preços inválidos: {self.precos_invalidos}",
                (
                    "Preços antigos removidos: "
                    f"{self.precos_antigos_removidos}"
                ),
                (
                    "Descontos divergentes: "
                    f"{self.descontos_divergentes}"
                ),
                (
                    "Descontos fora do intervalo: "
                    f"{self.descontos_fora_intervalo}"
                ),
                (
                    "Descontos acima do limite confiável: "
                    f"{self.descontos_acima_limite}"
                ),
                separador,
            ]
        )


class ValidadorOferta:
    """
    Valida e normaliza os dados comerciais de uma oferta.

    Problemas graves marcam a oferta como inválida.
    Problemas limitados ao preço antigo removem apenas o
    preço antigo, preservando a oferta e o preço atual.
    """

    def __init__(
        self,
        tolerancia_desconto: float = 2.0,
        desconto_maximo_confiavel: float = 90.0
    ) -> None:
        if tolerancia_desconto < 0:
            raise ValueError(
                "A tolerância de desconto não pode ser negativa."
            )

        if not 0 < desconto_maximo_confiavel <= 100:
            raise ValueError(
                "O desconto máximo confiável deve estar entre 0 e 100."
            )

        self.tolerancia_desconto = tolerancia_desconto
        self.desconto_maximo_confiavel = (
            desconto_maximo_confiavel
        )

    def validar(
        self,
        oferta: Oferta,
        estatisticas: EstatisticasValidacao | None = None
    ) -> Oferta:
        oferta.valida = True
        oferta.motivos_validacao.clear()

        if estatisticas is not None:
            estatisticas.ofertas_recebidas += 1

        self._validar_dados_obrigatorios(
            oferta,
            estatisticas
        )

        self._normalizar_desconto_anunciado(
            oferta,
            estatisticas
        )

        self._validar_preco_antigo(
            oferta,
            estatisticas
        )

        if estatisticas is not None:
            if oferta.valida:
                estatisticas.ofertas_validas += 1
            else:
                estatisticas.ofertas_invalidas += 1

        return oferta

    def _validar_dados_obrigatorios(
        self,
        oferta: Oferta,
        estatisticas: EstatisticasValidacao | None
    ) -> None:
        if not oferta.nome.strip():
            if estatisticas is not None:
                estatisticas.nomes_vazios += 1

            self._invalidar(
                oferta,
                "Nome da oferta vazio."
            )

        if oferta.preco <= 0:
            if estatisticas is not None:
                estatisticas.precos_invalidos += 1

            self._invalidar(
                oferta,
                "Preço atual menor ou igual a zero."
            )

        if not self._link_valido(
            oferta.link
        ):
            if estatisticas is not None:
                estatisticas.links_invalidos += 1

            self._invalidar(
                oferta,
                "Link da oferta inválido."
            )

    @staticmethod
    def _normalizar_desconto_anunciado(
        oferta: Oferta,
        estatisticas: EstatisticasValidacao | None
    ) -> None:
        desconto = oferta.desconto_anunciado

        if desconto is None:
            return

        if desconto < 0 or desconto > 100:
            oferta.desconto_anunciado = None

            if estatisticas is not None:
                estatisticas.descontos_fora_intervalo += 1

            ValidadorOferta._adicionar_motivo(
                oferta,
                "Desconto anunciado fora do intervalo de 0% a 100%."
            )

            logger.debug(
                (
                    "Desconto anunciado removido da oferta '%s'. "
                    "Motivo: valor fora do intervalo de 0%% a 100%%."
                ),
                oferta.nome
            )

            return

        oferta.desconto_anunciado = round(
            desconto,
            2
        )

    def _validar_preco_antigo(
        self,
        oferta: Oferta,
        estatisticas: EstatisticasValidacao | None
    ) -> None:
        preco_antigo = oferta.preco_antigo

        if preco_antigo is None:
            return

        if preco_antigo <= 0:
            self._remover_preco_antigo(
                oferta,
                "Preço antigo menor ou igual a zero.",
                estatisticas
            )
            return

        if preco_antigo <= oferta.preco:
            self._remover_preco_antigo(
                oferta,
                "Preço antigo menor ou igual ao preço atual.",
                estatisticas
            )
            return

        desconto_calculado = oferta.desconto_percentual

        if desconto_calculado > self.desconto_maximo_confiavel:
            if estatisticas is not None:
                estatisticas.descontos_acima_limite += 1

            self._remover_preco_antigo(
                oferta,
                (
                    "Desconto calculado acima do limite confiável: "
                    f"{desconto_calculado:.2f}%."
                ),
                estatisticas
            )
            return

        desconto_anunciado = oferta.desconto_anunciado

        if desconto_anunciado is None:
            return

        divergencia = abs(
            desconto_calculado
            - desconto_anunciado
        )

        if divergencia <= self.tolerancia_desconto:
            return

        if estatisticas is not None:
            estatisticas.descontos_divergentes += 1

        self._remover_preco_antigo(
            oferta,
            (
                "Divergência entre o desconto anunciado "
                f"({desconto_anunciado:.2f}%) e o calculado "
                f"({desconto_calculado:.2f}%)."
            ),
            estatisticas
        )

    @staticmethod
    def _link_valido(
        link: str
    ) -> bool:
        if not link or not link.strip():
            return False

        resultado = urlparse(
            link.strip()
        )

        return (
            resultado.scheme in {
                "http",
                "https"
            }
            and bool(resultado.netloc)
        )

    @staticmethod
    def _invalidar(
        oferta: Oferta,
        motivo: str
    ) -> None:
        oferta.valida = False

        ValidadorOferta._adicionar_motivo(
            oferta,
            motivo
        )

        logger.warning(
            "Oferta marcada como inválida: '%s' | Motivo: %s",
            oferta.nome,
            motivo
        )

    @staticmethod
    def _remover_preco_antigo(
        oferta: Oferta,
        motivo: str,
        estatisticas: EstatisticasValidacao | None
    ) -> None:
        oferta.preco_antigo = None

        if estatisticas is not None:
            estatisticas.precos_antigos_removidos += 1

        ValidadorOferta._adicionar_motivo(
            oferta,
            motivo
        )

        logger.debug(
            (
                "Preço antigo removido da oferta '%s'. "
                "Motivo: %s"
            ),
            oferta.nome,
            motivo
        )

    @staticmethod
    def _adicionar_motivo(
        oferta: Oferta,
        motivo: str
    ) -> None:
        if motivo not in oferta.motivos_validacao:
            oferta.motivos_validacao.append(
                motivo
            )
