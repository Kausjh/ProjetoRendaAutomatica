from __future__ import annotations

import re
import unicodedata

from models.catalogo_canonico import ResultadoObservacaoCatalogoCanonico
from models.oferta import Oferta
from repositories.catalogo_canonico_repository import (
    CatalogoCanonicoRepository,
)


class CatalogoCanonicoService:
    def __init__(
        self,
        repository: CatalogoCanonicoRepository,
        *,
        confianca_minima: float = 90.0,
    ) -> None:
        if not 0 <= confianca_minima <= 100:
            raise ValueError("confianca_minima precisa estar entre 0 e 100.")

        self.repository = repository
        self.confianca_minima = float(confianca_minima)

    def observar(
        self,
        oferta: Oferta,
    ) -> ResultadoObservacaoCatalogoCanonico:
        chave_canonica = self._texto(oferta.chave_produto_canonica)
        nome_canonico = self._texto(oferta.produto_canonico)
        confianca = float(oferta.confianca_normalizacao or 0.0)

        if not chave_canonica or not nome_canonico:
            return self._resultado_ignorado(
                status="ignorado_sem_identidade",
                motivo="Oferta sem identidade canonica deterministica.",
                chave_canonica=chave_canonica,
            )

        if confianca < self.confianca_minima:
            return self._resultado_ignorado(
                status="ignorado_baixa_confianca",
                motivo=("Confianca de normalizacao abaixo " "do piso do Catalogo Canonico."),
                chave_canonica=chave_canonica,
            )

        marketplace = self._normalizar_marketplace(oferta.marketplace or oferta.loja)

        if not marketplace:
            return self._resultado_ignorado(
                status="ignorado_sem_marketplace",
                motivo=("Marketplace ausente para vincular " "o anuncio ao produto canonico."),
                chave_canonica=chave_canonica,
            )

        identificador = self._identificador_anuncio(oferta)

        if not identificador:
            return ResultadoObservacaoCatalogoCanonico(
                status="ignorado_sem_identificador_anuncio",
                registrado=False,
                chave_canonica=chave_canonica,
                marketplace=marketplace,
                identificador_anuncio=None,
                motivo=(
                    "Anuncio sem id_anuncio/id_produto; " "nenhum merge por URL e permitido no V1."
                ),
            )

        status = self.repository.registrar_observacao(
            chave_canonica=chave_canonica,
            nome_canonico=nome_canonico,
            categoria=self._texto(oferta.categoria),
            marca=self._texto(oferta.marca),
            modelo=self._texto(oferta.modelo_produto),
            confianca=confianca,
            marketplace=marketplace,
            identificador=identificador,
            id_anuncio=self._texto(oferta.id_anuncio),
            id_produto=self._texto(oferta.id_produto),
            link=str(oferta.link or "").strip(),
            loja=self._texto(oferta.loja),
        )

        if status == "conflito_anuncio":
            return ResultadoObservacaoCatalogoCanonico(
                status=status,
                registrado=False,
                chave_canonica=chave_canonica,
                marketplace=marketplace,
                identificador_anuncio=identificador,
                motivo=(
                    "O mesmo anuncio ja esta ligado a outra "
                    "chave canonica; remapeamento automatico bloqueado."
                ),
            )

        return ResultadoObservacaoCatalogoCanonico(
            status=status,
            registrado=True,
            chave_canonica=chave_canonica,
            marketplace=marketplace,
            identificador_anuncio=identificador,
            motivo="Observacao persistida no Catalogo Canonico V1.",
        )

    @staticmethod
    def _texto(valor) -> str | None:
        texto = str(valor or "").strip()
        return texto or None

    @classmethod
    def _normalizar_marketplace(cls, valor) -> str:
        texto = cls._texto(valor)

        if not texto:
            return ""

        sem_acento = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(caractere)
        ).casefold()

        normalizado = re.sub(
            r"[^a-z0-9]+",
            "_",
            sem_acento,
        ).strip("_")

        aliases = {
            "mercado_livre": "mercado_livre",
            "mercadolivre": "mercado_livre",
            "ml": "mercado_livre",
            "kabum": "kabum",
            "ka_bum": "kabum",
        }

        return aliases.get(normalizado, normalizado)

    @staticmethod
    def _identificador_anuncio(
        oferta: Oferta,
    ) -> str | None:
        for valor in (
            oferta.id_anuncio,
            oferta.id_produto,
        ):
            texto = str(valor or "").strip()

            if texto:
                return texto

        return None

    @staticmethod
    def _resultado_ignorado(
        *,
        status: str,
        motivo: str,
        chave_canonica: str | None,
    ) -> ResultadoObservacaoCatalogoCanonico:
        return ResultadoObservacaoCatalogoCanonico(
            status=status,
            registrado=False,
            chave_canonica=chave_canonica,
            marketplace=None,
            identificador_anuncio=None,
            motivo=motivo,
        )
