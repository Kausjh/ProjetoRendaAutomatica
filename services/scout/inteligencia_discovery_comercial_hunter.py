# 63.8738, -149.7525

from __future__ import annotations

import math
import re
from collections.abc import (
    Iterable,
    Mapping,
)

from models.sinal_discovery_comercial_hunter import (
    ResultadoDiscoveryComercialHunter,
    SinalDiscoveryComercialHunter,
)
from models.tendencia_comercial_scout import (
    TendenciaComercialScout,
)


class InteligenciaDiscoveryComercialHunter:
    """
    Converte tendencias comerciais maduras em sugestoes
    conservadoras de budget para o Hunter.

    Esta camada atua somente em discovery.

    Ela nao valida preco, nao altera score, nao altera
    Verifier, nao aprova oferta e nao publica nada.
    """

    FATOR_AUMENTO_PADRAO = 0.50
    AUMENTO_MAXIMO_PADRAO = 10

    DIMENSAO_MARKETPLACE = "marketplace"
    DIRECAO_ALTA = "alta"

    EVIDENCIA_QUALIDADE_TEMPORAL = "qualidade_temporal:aprovada"

    EVIDENCIA_AMBAS_METADES = "ambas_metades_tem_sinais"

    MARKETPLACE_PARA_FONTE = {
        "mercadolivre": ("MercadoLivreScraper"),
        "ml": ("MercadoLivreScraper"),
        "shopee": ("ShopeeScraper"),
        "kabum": ("KabumScraper"),
        "aliexpress": ("AliExpressScraper"),
    }

    def __init__(
        self,
        *,
        fator_aumento: float = (FATOR_AUMENTO_PADRAO),
        aumento_maximo: int = (AUMENTO_MAXIMO_PADRAO),
    ) -> None:
        fator = float(fator_aumento)

        if fator <= 0 or fator > 1:
            raise ValueError("fator_aumento precisa ficar " "entre 0 e 1.")

        if (
            isinstance(
                aumento_maximo,
                bool,
            )
            or not isinstance(
                aumento_maximo,
                int,
            )
            or aumento_maximo <= 0
        ):
            raise ValueError("aumento_maximo precisa ser " "inteiro positivo.")

        self.fator_aumento = fator
        self.aumento_maximo = aumento_maximo

    def calcular(
        self,
        limites_base: Mapping[
            str,
            int,
        ],
        tendencias: Iterable[TendenciaComercialScout],
    ) -> ResultadoDiscoveryComercialHunter:
        base = self._normalizar_limites(limites_base)

        sugeridos = dict(base)

        melhores_por_fonte: dict[
            str,
            TendenciaComercialScout,
        ] = {}

        for tendencia in tendencias:

            fonte = self._fonte_da_tendencia(tendencia)

            if fonte is None:
                continue

            if fonte not in base:
                continue

            anterior = melhores_por_fonte.get(fonte)

            if anterior is None or tendencia.sinais_distintos > anterior.sinais_distintos:
                melhores_por_fonte[fonte] = tendencia

        sinais: list[SinalDiscoveryComercialHunter] = []

        for fonte in base:

            tendencia = melhores_por_fonte.get(fonte)

            if tendencia is None:
                continue

            limite_base = base[fonte]

            aumento = max(
                1,
                math.ceil(limite_base * self.fator_aumento),
            )

            aumento = min(
                aumento,
                self.aumento_maximo,
            )

            limite_sugerido = limite_base + aumento

            sugeridos[fonte] = limite_sugerido

            sinais.append(
                SinalDiscoveryComercialHunter(
                    fonte_hunter=fonte,
                    marketplace=(tendencia.chave),
                    direcao=(tendencia.direcao),
                    sinais_distintos=(tendencia.sinais_distintos),
                    limite_base=(limite_base),
                    limite_sugerido=(limite_sugerido),
                    motivo=("tendencia_marketplace_" "alta_temporalmente_madura"),
                )
            )

        return ResultadoDiscoveryComercialHunter(
            limites_base=tuple(base.items()),
            limites_sugeridos=tuple(sugeridos.items()),
            sinais=tuple(sinais),
        )

    @classmethod
    def _fonte_da_tendencia(
        cls,
        tendencia: TendenciaComercialScout,
    ) -> str | None:
        if tendencia.dimensao != cls.DIMENSAO_MARKETPLACE:
            return None

        if tendencia.direcao != cls.DIRECAO_ALTA:
            return None

        evidencias = set(tendencia.evidencias)

        if cls.EVIDENCIA_QUALIDADE_TEMPORAL not in evidencias:
            return None

        if cls.EVIDENCIA_AMBAS_METADES not in evidencias:
            return None

        marketplace = cls._normalizar_marketplace(tendencia.chave)

        return cls.MARKETPLACE_PARA_FONTE.get(marketplace)

    @staticmethod
    def _normalizar_marketplace(
        valor: object,
    ) -> str:
        texto = str(valor or "").strip().casefold()

        return re.sub(
            r"[^a-z0-9]+",
            "",
            texto,
        )

    @staticmethod
    def _normalizar_limites(
        limites: Mapping[
            str,
            int,
        ],
    ) -> dict[str, int]:
        resultado: dict[
            str,
            int,
        ] = {}

        for fonte, limite in limites.items():
            nome = str(fonte or "").strip()

            if not nome:
                raise ValueError("Nome de fonte Hunter " "invalido.")

            if (
                isinstance(
                    limite,
                    bool,
                )
                or not isinstance(
                    limite,
                    int,
                )
                or limite <= 0
            ):
                raise ValueError("Limite Hunter precisa ser " "inteiro positivo.")

            resultado[nome] = limite

        return resultado
