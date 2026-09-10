# 63.8738, -149.7525

from __future__ import annotations

import logging
from collections.abc import Mapping
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from dataclasses import dataclass

from models.oferta import Oferta
from models.resultado_hunter_v2 import (
    CandidatoHunterV2,
    DuplicataHunterV2,
    ResultadoFonteHunterV2,
    ResultadoHunterV2,
)
from scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class _ColetaFonte:
    indice: int
    fonte: str
    limite: int
    ofertas: tuple[Oferta, ...]
    erro: str | None = None


class HunterV2:
    """
    Orquestrador de descoberta de alto recall.

    O Hunter coleta candidatos e preserva recall.
    Validacao, classificacao, pontuacao e publicacao
    pertencem as camadas posteriores.
    """

    def __init__(
        self,
        scrapers: list[BaseScraper],
    ) -> None:
        self.scrapers = list(scrapers)

    @staticmethod
    def _nome_fonte(
        scraper: BaseScraper,
    ) -> str:
        return type(scraper).__name__

    @staticmethod
    def _validar_limite(
        limite: object,
        *,
        nome: str,
    ) -> int:
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
            raise ValueError(f"{nome} precisa ser inteiro positivo.")

        return limite

    def _limite_fonte(
        self,
        *,
        scraper: BaseScraper,
        limite_base: int,
        limites_por_fonte: Mapping[str, int],
    ) -> int:
        fonte = self._nome_fonte(scraper)

        limite = limites_por_fonte.get(
            fonte,
            limite_base,
        )

        return self._validar_limite(
            limite,
            nome=f"Limite de {fonte}",
        )

    def _executar_fonte(
        self,
        *,
        indice: int,
        scraper: BaseScraper,
        limite: int,
    ) -> _ColetaFonte:
        fonte = self._nome_fonte(scraper)

        logger.info(
            "Hunter V2 executando fonte '%s' com limite %s.",
            fonte,
            limite,
        )

        try:
            resultado = scraper.buscar_ofertas(limite=limite)

            if not isinstance(
                resultado,
                list,
            ):
                raise TypeError("Scraper nao retornou list.")

            ofertas = []

            for item in resultado:
                if not isinstance(
                    item,
                    Oferta,
                ):
                    raise TypeError("Scraper retornou item que nao e Oferta.")

                ofertas.append(item)

        except Exception as erro:
            logger.exception(
                "Hunter V2 isolou falha na fonte '%s'.",
                fonte,
            )

            return _ColetaFonte(
                indice=indice,
                fonte=fonte,
                limite=limite,
                ofertas=(),
                erro=(f"{type(erro).__name__}: " f"{erro}"),
            )

        logger.info(
            "Hunter V2: fonte '%s' entregou %s candidata(s).",
            fonte,
            len(ofertas),
        )

        return _ColetaFonte(
            indice=indice,
            fonte=fonte,
            limite=limite,
            ofertas=tuple(ofertas),
        )

    @staticmethod
    def _chave_identidade_segura(
        oferta: Oferta,
    ) -> tuple[str, ...]:
        marketplace = str(oferta.marketplace or "").strip().casefold()

        id_anuncio = str(oferta.id_anuncio or "").strip()

        if marketplace and id_anuncio:
            return (
                "anuncio",
                marketplace,
                id_anuncio,
            )

        link = str(oferta.link or "").strip()

        if link:
            return (
                "link_exato",
                link,
            )

        return (
            "objeto",
            str(id(oferta)),
        )

    @classmethod
    def _deduplicar(
        cls,
        coletas: list[_ColetaFonte],
    ) -> tuple[
        tuple[CandidatoHunterV2, ...],
        tuple[DuplicataHunterV2, ...],
    ]:
        candidatos: list[CandidatoHunterV2] = []

        duplicatas: list[DuplicataHunterV2] = []

        indice_por_chave: dict[
            tuple[str, ...],
            int,
        ] = {}

        for coleta in coletas:
            for oferta in coleta.ofertas:
                chave = cls._chave_identidade_segura(oferta)

                indice_existente = indice_por_chave.get(chave)

                if indice_existente is None:
                    indice_por_chave[chave] = len(candidatos)

                    candidatos.append(
                        CandidatoHunterV2(
                            oferta=oferta,
                            fontes=(coleta.fonte,),
                        )
                    )

                    continue

                existente = candidatos[indice_existente]

                duplicatas.append(
                    DuplicataHunterV2(
                        oferta=oferta,
                        representante=(existente.oferta),
                        fonte=coleta.fonte,
                        tipo_identidade=chave[0],
                    )
                )

                if coleta.fonte in existente.fontes:
                    continue

                candidatos[indice_existente] = CandidatoHunterV2(
                    oferta=existente.oferta,
                    fontes=(existente.fontes + (coleta.fonte,)),
                )

        return (
            tuple(candidatos),
            tuple(duplicatas),
        )

    def descobrir(
        self,
        limite_base: int,
        *,
        limites_por_fonte: (
            Mapping[
                str,
                int,
            ]
            | None
        ) = None,
    ) -> ResultadoHunterV2:
        limite_base = self._validar_limite(
            limite_base,
            nome="Limite base",
        )

        limites = dict(limites_por_fonte or {})

        for fonte, limite in limites.items():
            if (
                not isinstance(
                    fonte,
                    str,
                )
                or not fonte.strip()
            ):
                raise ValueError("Nome de fonte invalido.")

            self._validar_limite(
                limite,
                nome=f"Limite de {fonte}",
            )

        if not self.scrapers:
            return ResultadoHunterV2(
                candidatos=(),
                fontes=(),
                duplicatas=(),
                quantidade_bruta=0,
                quantidade_unica=0,
                duplicadas_confirmadas=0,
            )

        coletas_por_indice: dict[
            int,
            _ColetaFonte,
        ] = {}

        with ThreadPoolExecutor(
            max_workers=max(
                1,
                len(self.scrapers),
            )
        ) as executor:
            tarefas = {}

            for indice, scraper in enumerate(self.scrapers):
                limite = self._limite_fonte(
                    scraper=scraper,
                    limite_base=limite_base,
                    limites_por_fonte=limites,
                )

                tarefa = executor.submit(
                    self._executar_fonte,
                    indice=indice,
                    scraper=scraper,
                    limite=limite,
                )

                tarefas[tarefa] = indice

            for tarefa in as_completed(tarefas):
                coleta = tarefa.result()

                coletas_por_indice[coleta.indice] = coleta

        coletas = [coletas_por_indice[indice] for indice in range(len(self.scrapers))]

        quantidade_bruta = sum(len(coleta.ofertas) for coleta in coletas)

        candidatos, duplicatas = self._deduplicar(coletas)

        fontes = tuple(
            ResultadoFonteHunterV2(
                fonte=coleta.fonte,
                limite_solicitado=(coleta.limite),
                quantidade_coletada=len(coleta.ofertas),
                erro=coleta.erro,
            )
            for coleta in coletas
        )

        resultado = ResultadoHunterV2(
            candidatos=candidatos,
            fontes=fontes,
            duplicatas=duplicatas,
            quantidade_bruta=(quantidade_bruta),
            quantidade_unica=len(candidatos),
            duplicadas_confirmadas=len(duplicatas),
        )

        logger.info(
            (
                "Hunter V2 concluido: "
                "%s bruta(s), %s unica(s), "
                "%s duplicada(s), "
                "%s fonte(s) com erro."
            ),
            resultado.quantidade_bruta,
            resultado.quantidade_unica,
            resultado.duplicadas_confirmadas,
            len(resultado.fontes_com_erro),
        )

        return resultado
