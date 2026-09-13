from __future__ import annotations

import math
from datetime import UTC, datetime

from models.catalogo_canonico import (
    ResultadoObservacaoCatalogoCanonico,
)
from models.oferta import Oferta
from models.price_intelligence import (
    ResultadoObservacaoPriceIntelligence,
)
from repositories.price_intelligence_repository import (
    PriceIntelligenceRepository,
)


class PriceIntelligenceService:
    def __init__(
        self,
        repository: PriceIntelligenceRepository,
        *,
        confianca_minima: float = 90.0,
    ) -> None:
        if not 0 <= confianca_minima <= 100:
            raise ValueError("confianca_minima precisa estar entre 0 e 100.")

        self.repository = repository
        self.confianca_minima = float(confianca_minima)

    def observar(
        self,
        *,
        oferta: Oferta,
        resultado_catalogo: ResultadoObservacaoCatalogoCanonico,
    ) -> ResultadoObservacaoPriceIntelligence:
        if not resultado_catalogo.registrado:
            return self._ignorado(
                status="ignorado_catalogo_nao_registrado",
                motivo=("Canonical Catalog nao confirmou " "a identidade deste anuncio."),
                resultado_catalogo=resultado_catalogo,
            )

        chave = self._texto(oferta.chave_produto_canonica)
        nome = self._texto(oferta.produto_canonico)

        if not chave or not nome or chave != resultado_catalogo.chave_canonica:
            return self._ignorado(
                status="ignorado_inconsistencia_canonica",
                motivo=("Oferta e Canonical Catalog divergem " "sobre a identidade canonica."),
                resultado_catalogo=resultado_catalogo,
            )

        marketplace = self._texto(resultado_catalogo.marketplace)
        identificador = self._texto(resultado_catalogo.identificador_anuncio)

        if not marketplace or not identificador:
            return self._ignorado(
                status="ignorado_catalogo_sem_listing",
                motivo=("Canonical Catalog nao forneceu " "marketplace e identificador."),
                resultado_catalogo=resultado_catalogo,
            )

        confianca = float(oferta.confianca_normalizacao or 0.0)

        if confianca < self.confianca_minima:
            return self._ignorado(
                status="ignorado_baixa_confianca",
                motivo=("Confianca canonica abaixo do piso " "do Price Intelligence."),
                resultado_catalogo=resultado_catalogo,
            )

        try:
            preco = float(oferta.preco)
        except (TypeError, ValueError):
            preco = 0.0

        if not math.isfinite(preco) or preco <= 0:
            return self._ignorado(
                status="ignorado_preco_invalido",
                motivo=("Preco oficial invalido para " "Price Intelligence."),
                resultado_catalogo=resultado_catalogo,
            )

        status, nova_observacao = self.repository.registrar_observacao(
            chave_canonica=chave,
            nome_canonico=nome,
            marketplace=marketplace,
            identificador=identificador,
            preco=preco,
            link=self._texto(oferta.link) or "",
            observado_em=datetime.now(UTC).isoformat(),
        )

        if status == "conflito_identidade":
            return ResultadoObservacaoPriceIntelligence(
                status=status,
                registrado=False,
                nova_observacao_historica=False,
                chave_canonica=chave,
                marketplace=marketplace,
                identificador=identificador,
                preco=preco,
                motivo=("Listing ja estava ligado a outra " "identidade no Price Intelligence."),
            )

        return ResultadoObservacaoPriceIntelligence(
            status=status,
            registrado=True,
            nova_observacao_historica=nova_observacao,
            chave_canonica=chave,
            marketplace=marketplace,
            identificador=identificador,
            preco=preco,
            motivo=("Preco oficial observado sobre " "identidade canonica confirmada."),
        )

    @staticmethod
    def _texto(
        valor,
    ) -> str | None:
        texto = str(valor or "").strip()

        return texto or None

    @staticmethod
    def _ignorado(
        *,
        status: str,
        motivo: str,
        resultado_catalogo: ResultadoObservacaoCatalogoCanonico,
    ) -> ResultadoObservacaoPriceIntelligence:
        return ResultadoObservacaoPriceIntelligence(
            status=status,
            registrado=False,
            nova_observacao_historica=False,
            chave_canonica=(resultado_catalogo.chave_canonica),
            marketplace=(resultado_catalogo.marketplace),
            identificador=(resultado_catalogo.identificador_anuncio),
            preco=None,
            motivo=motivo,
        )
