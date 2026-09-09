# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True)
class ResultadoInteligenciaSinalPreco:
    status: str
    confirmado: bool

    preco_oficial: float | None
    preco_condicional: float | None

    codigo_cupom: str | None
    cupom_validado: bool

    economia_percentual: float
    confianca: float

    motivos: tuple[str, ...]


class InteligenciaSinalPreco:
    """Interpreta sinais externos de preco.

    Regra fundamental:

        observado != confirmado

    Oferta.preco continua sendo o preco oficial.
    """

    STATUS_SEM_SINAL = "sem_sinal"
    STATUS_OBSERVADO = "observado"
    STATUS_CONFIRMADO = "confirmado"

    ORIGEM_SOCIAL_SCOUT = "social_scout"

    def analisar(
        self,
        oferta: Oferta,
    ) -> ResultadoInteligenciaSinalPreco:
        preco_oficial = self._preco_positivo(oferta.preco)

        preco_condicional = self._preco_positivo(oferta.preco_condicional_observado)

        codigo_cupom = str(oferta.codigo_cupom_observado or "").strip() or None

        cupom_validado = bool(oferta.cupom_validado_descoberta)

        origem = str(oferta.origem_descoberta or "").strip().casefold()

        if origem != self.ORIGEM_SOCIAL_SCOUT:
            return self._resultado(
                status=self.STATUS_SEM_SINAL,
                confirmado=False,
                preco_oficial=preco_oficial,
                preco_condicional=preco_condicional,
                codigo_cupom=codigo_cupom,
                cupom_validado=cupom_validado,
                economia=0.0,
                confianca=0.0,
                motivos=("origem_sem_sinal_social",),
            )

        if preco_oficial is None:
            return self._resultado(
                status=self.STATUS_SEM_SINAL,
                confirmado=False,
                preco_oficial=None,
                preco_condicional=preco_condicional,
                codigo_cupom=codigo_cupom,
                cupom_validado=cupom_validado,
                economia=0.0,
                confianca=0.0,
                motivos=("preco_oficial_ausente",),
            )

        if preco_condicional is None:
            return self._resultado(
                status=self.STATUS_SEM_SINAL,
                confirmado=False,
                preco_oficial=preco_oficial,
                preco_condicional=None,
                codigo_cupom=codigo_cupom,
                cupom_validado=cupom_validado,
                economia=0.0,
                confianca=20.0,
                motivos=("preco_condicional_ausente",),
            )

        if preco_condicional >= preco_oficial:
            return self._resultado(
                status=self.STATUS_OBSERVADO,
                confirmado=False,
                preco_oficial=preco_oficial,
                preco_condicional=preco_condicional,
                codigo_cupom=codigo_cupom,
                cupom_validado=cupom_validado,
                economia=0.0,
                confianca=30.0,
                motivos=("preco_condicional_nao_melhora_oficial",),
            )

        economia = self._economia_percentual(
            preco_oficial=preco_oficial,
            preco_condicional=preco_condicional,
        )

        if not cupom_validado:
            return self._resultado(
                status=self.STATUS_OBSERVADO,
                confirmado=False,
                preco_oficial=preco_oficial,
                preco_condicional=preco_condicional,
                codigo_cupom=codigo_cupom,
                cupom_validado=False,
                economia=economia,
                confianca=45.0,
                motivos=(
                    "preco_condicional_melhor_que_oficial",
                    "condicao_ainda_nao_validada",
                ),
            )

        return self._resultado(
            status=self.STATUS_CONFIRMADO,
            confirmado=True,
            preco_oficial=preco_oficial,
            preco_condicional=preco_condicional,
            codigo_cupom=codigo_cupom,
            cupom_validado=True,
            economia=economia,
            confianca=100.0,
            motivos=(
                "preco_condicional_melhor_que_oficial",
                "condicao_validada",
            ),
        )

    def aplicar(
        self,
        oferta: Oferta,
    ) -> ResultadoInteligenciaSinalPreco:
        resultado = self.analisar(oferta)

        oferta.status_sinal_preco = resultado.status

        oferta.confianca_sinal_preco = resultado.confianca

        oferta.economia_condicional_percentual = resultado.economia_percentual

        oferta.motivos_sinal_preco = list(resultado.motivos)

        return resultado

    @staticmethod
    def _preco_positivo(
        valor,
    ) -> float | None:
        if isinstance(
            valor,
            bool,
        ):
            return None

        if valor is None:
            return None

        try:
            numero = float(valor)

        except (
            TypeError,
            ValueError,
        ):
            return None

        if numero <= 0:
            return None

        return round(
            numero,
            2,
        )

    @staticmethod
    def _economia_percentual(
        *,
        preco_oficial: float,
        preco_condicional: float,
    ) -> float:
        if preco_oficial <= 0:
            return 0.0

        economia = (preco_oficial - preco_condicional) / preco_oficial * 100.0

        return round(
            max(
                economia,
                0.0,
            ),
            2,
        )

    @staticmethod
    def _resultado(
        *,
        status: str,
        confirmado: bool,
        preco_oficial: float | None,
        preco_condicional: float | None,
        codigo_cupom: str | None,
        cupom_validado: bool,
        economia: float,
        confianca: float,
        motivos: tuple[str, ...],
    ) -> ResultadoInteligenciaSinalPreco:
        return ResultadoInteligenciaSinalPreco(
            status=status,
            confirmado=confirmado,
            preco_oficial=preco_oficial,
            preco_condicional=preco_condicional,
            codigo_cupom=codigo_cupom,
            cupom_validado=cupom_validado,
            economia_percentual=round(
                float(economia),
                2,
            ),
            confianca=round(
                float(confianca),
                2,
            ),
            motivos=motivos,
        )
