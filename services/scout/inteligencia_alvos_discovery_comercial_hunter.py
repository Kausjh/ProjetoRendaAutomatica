# 63.8738, -149.7525

from __future__ import annotations

from collections.abc import Iterable

from models.alvo_discovery_comercial_hunter import (
    AlvoDiscoveryComercialHunter,
    ResultadoAlvosDiscoveryComercialHunter,
)
from models.tendencia_comercial_scout import (
    TendenciaComercialScout,
)
from services.scout.agregador_tendencias_comerciais_scout import (
    AgregadorTendenciasComerciaisScout,
)


class InteligenciaAlvosDiscoveryComercialHunter:
    """
    Converte rotas comerciais temporalmente maduras em alvos de discovery.

    Esta camada nao executa scraper, nao altera budget e nao publica.
    Ela apenas transforma evidencia comercial em alvos estruturados
    que poderao ser consumidos pelo Hunter em uma etapa posterior.
    """

    DIMENSAO_ROTA_DISCOVERY = AgregadorTendenciasComerciaisScout.DIMENSAO_ROTA_DISCOVERY

    SEPARADOR_ROTA_DISCOVERY = AgregadorTendenciasComerciaisScout.SEPARADOR_ROTA_DISCOVERY

    DIRECOES_ACEITAS = frozenset(
        {
            "alta",
            "estavel",
        }
    )

    EVIDENCIA_QUALIDADE_TEMPORAL = "qualidade_temporal:aprovada"
    EVIDENCIA_AMBAS_METADES = "ambas_metades_tem_sinais"

    ROTAS_SUPORTADAS = {
        (
            "kabum",
            "buscar_termos_kabum",
        ): (
            "KabumScraper",
            True,
        ),
        (
            "aliexpress",
            "feed_curado_aliexpress",
        ): (
            "AliExpressScraper",
            False,
        ),
    }

    def calcular(
        self,
        tendencias: Iterable[TendenciaComercialScout],
    ) -> ResultadoAlvosDiscoveryComercialHunter:
        alvos: list[AlvoDiscoveryComercialHunter] = []
        vistos: set[
            tuple[
                str,
                str,
                str,
                str | None,
            ]
        ] = set()

        for tendencia in tendencias:
            alvo = self._converter_tendencia(
                tendencia,
            )

            if alvo is None:
                continue

            identidade = (
                alvo.fonte_hunter,
                alvo.marketplace,
                alvo.estrategia,
                (alvo.termo_busca.casefold() if alvo.termo_busca else None),
            )

            if identidade in vistos:
                continue

            vistos.add(identidade)
            alvos.append(alvo)

        alvos.sort(
            key=lambda item: (
                -item.sinais_distintos,
                item.fonte_hunter,
                item.estrategia,
                (item.termo_busca or "").casefold(),
            )
        )

        return ResultadoAlvosDiscoveryComercialHunter(
            alvos=tuple(alvos),
        )

    @classmethod
    def _converter_tendencia(
        cls,
        tendencia: TendenciaComercialScout,
    ) -> AlvoDiscoveryComercialHunter | None:
        if tendencia.dimensao != cls.DIMENSAO_ROTA_DISCOVERY:
            return None

        if tendencia.direcao not in cls.DIRECOES_ACEITAS:
            return None

        evidencias = set(tendencia.evidencias)

        if cls.EVIDENCIA_QUALIDADE_TEMPORAL not in evidencias:
            return None

        if cls.EVIDENCIA_AMBAS_METADES not in evidencias:
            return None

        rota = cls._decodificar_rota(
            tendencia.chave,
        )

        if rota is None:
            return None

        (
            marketplace,
            estrategia,
            termo,
        ) = rota

        configuracao = cls.ROTAS_SUPORTADAS.get(
            (
                marketplace,
                estrategia,
            )
        )

        if configuracao is None:
            return None

        (
            fonte_hunter,
            exige_termo,
        ) = configuracao

        termo_busca: str | None = None

        if exige_termo:
            termo_busca = str(tendencia.rotulo or termo).strip() or None

            if termo_busca is None:
                return None

        return AlvoDiscoveryComercialHunter(
            fonte_hunter=fonte_hunter,
            marketplace=marketplace,
            estrategia=estrategia,
            termo_busca=termo_busca,
            direcao=tendencia.direcao,
            sinais_distintos=(tendencia.sinais_distintos),
            motivo=("rota_comercial_" "temporalmente_madura"),
            evidencias=tuple(tendencia.evidencias),
        )

    @classmethod
    def _decodificar_rota(
        cls,
        valor: object,
    ) -> (
        tuple[
            str,
            str,
            str,
        ]
        | None
    ):
        partes = str(valor or "").split(
            cls.SEPARADOR_ROTA_DISCOVERY,
            2,
        )

        if len(partes) != 3:
            return None

        marketplace = partes[0].strip().casefold()
        estrategia = partes[1].strip().casefold()
        termo = partes[2].strip()

        if not marketplace or not estrategia:
            return None

        return (
            marketplace,
            estrategia,
            termo,
        )
