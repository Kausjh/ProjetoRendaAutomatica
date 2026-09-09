from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from models.oferta import Oferta
from repositories.historico_precos_efetivos_repository import (
    HistoricoPrecosEfetivosRepository,
)


@dataclass(frozen=True)
class ResultadoHistoricoPrecoEfetivo:
    elegivel: bool
    motivo: str
    chave_serie: str | None = None
    tipo_condicao: str | None = None
    preco_efetivo: float | None = None
    preco_anterior: float | None = None
    menor_preco_anterior: float | None = None
    novo_menor_preco: bool = False
    queda_percentual: float = 0.0
    primeiro_registro: bool = False
    quantidade_registros: int = 0
    novo_preco_registrado: bool = False


class HistoricoPrecosEfetivosService:
    def __init__(
        self,
        repository: HistoricoPrecosEfetivosRepository,
        tamanho_lote_salvamento: int = 20,
    ) -> None:
        if tamanho_lote_salvamento <= 0:
            raise ValueError("Tamanho do lote precisa ser positivo.")

        self.repository = repository
        self.tamanho_lote_salvamento = tamanho_lote_salvamento
        self._alteracoes_pendentes = 0

    def analisar_e_registrar(
        self,
        oferta: Oferta,
    ) -> ResultadoHistoricoPrecoEfetivo:
        elegibilidade = self._extrair_preco_efetivo_confirmado(oferta)

        if elegibilidade is None:
            return ResultadoHistoricoPrecoEfetivo(
                elegivel=False,
                motivo=("preco_efetivo_nao_confirmado"),
            )

        (
            preco_efetivo,
            tipo_condicao,
        ) = elegibilidade

        preco_oficial = float(oferta.preco)

        chave_produto = self._criar_chave_produto(oferta)

        marketplace = str(oferta.marketplace or oferta.loja or "desconhecido").strip().lower()

        chave_serie = self._criar_chave_serie(
            chave_produto=chave_produto,
            marketplace=marketplace,
            tipo_condicao=tipo_condicao,
        )

        registros_anteriores = self.repository.obter_registros(chave_serie)

        precos_anteriores = [
            float(registro["preco_efetivo"])
            for registro in registros_anteriores
            if self._preco_valido(registro.get("preco_efetivo"))
        ]

        primeiro_registro = len(precos_anteriores) == 0

        preco_anterior = precos_anteriores[-1] if precos_anteriores else None

        menor_preco_anterior = min(precos_anteriores) if precos_anteriores else None

        novo_menor_preco = menor_preco_anterior is not None and preco_efetivo < menor_preco_anterior

        queda_percentual = self._calcular_queda_percentual(
            preco_anterior=preco_anterior,
            preco_atual=preco_efetivo,
        )

        coletado_em = (
            datetime.now()
            .astimezone()
            .isoformat(
                timespec="seconds",
            )
        )

        novo_preco_registrado = self.repository.registrar_preco_efetivo(
            chave_serie=chave_serie,
            chave_produto=chave_produto,
            marketplace=marketplace,
            tipo_condicao=tipo_condicao,
            preco_efetivo=preco_efetivo,
            preco_oficial=preco_oficial,
            coletado_em=coletado_em,
            fonte=(oferta.fonte_promocao_marketplace or "marketplace_oficial"),
            codigo_cupom_observado=(oferta.codigo_cupom_observado),
            codigo_cupom_validado=(oferta.cupom_validado_descoberta),
        )

        if novo_preco_registrado:
            self._alteracoes_pendentes += 1

        if self._alteracoes_pendentes >= self.tamanho_lote_salvamento:
            self.salvar_pendentes()

        quantidade_registros = len(self.repository.obter_registros(chave_serie))

        return ResultadoHistoricoPrecoEfetivo(
            elegivel=True,
            motivo="preco_efetivo_confirmado",
            chave_serie=chave_serie,
            tipo_condicao=tipo_condicao,
            preco_efetivo=preco_efetivo,
            preco_anterior=preco_anterior,
            menor_preco_anterior=(menor_preco_anterior),
            novo_menor_preco=(novo_menor_preco),
            queda_percentual=(queda_percentual),
            primeiro_registro=(primeiro_registro),
            quantidade_registros=(quantidade_registros),
            novo_preco_registrado=(novo_preco_registrado),
        )

    def salvar_pendentes(self) -> None:
        if self._alteracoes_pendentes <= 0:
            return

        self.repository.salvar()
        self._alteracoes_pendentes = 0

    @staticmethod
    def _extrair_preco_efetivo_confirmado(
        oferta: Oferta,
    ) -> tuple[float, str] | None:
        if oferta.promocao_marketplace_confirmada is not True:
            return None

        if oferta.preco_grupo_confere_promocao is not True:
            return None

        promocional = oferta.preco_promocional_marketplace

        if not (HistoricoPrecosEfetivosService._preco_valido(promocional)):
            return None

        if not (HistoricoPrecosEfetivosService._preco_valido(oferta.preco)):
            return None

        preco_efetivo = float(promocional)

        preco_oficial = float(oferta.preco)

        if preco_efetivo >= preco_oficial:
            return None

        tipo = str(oferta.tipo_promocao_marketplace or "promocao_marketplace").strip().lower()

        if not tipo:
            tipo = "promocao_marketplace"

        return (
            preco_efetivo,
            tipo,
        )

    @staticmethod
    def _criar_chave_produto(
        oferta: Oferta,
    ) -> str:
        for identificador in (
            oferta.id_produto,
            oferta.id_anuncio,
        ):
            if identificador:
                return (
                    str(identificador)
                    .strip()
                    .upper()
                    .replace(
                        "-",
                        "",
                    )
                    .replace(
                        "_",
                        "",
                    )
                )

        return oferta.link.strip()

    @classmethod
    def _criar_chave_serie(
        cls,
        *,
        chave_produto: str,
        marketplace: str,
        tipo_condicao: str,
    ) -> str:
        return "|".join(
            (
                chave_produto,
                cls._normalizar_segmento(marketplace),
                cls._normalizar_segmento(tipo_condicao),
            )
        )

    @staticmethod
    def _normalizar_segmento(
        valor: str,
    ) -> str:
        normalizado = re.sub(
            r"[^a-z0-9]+",
            "_",
            valor.lower(),
        )

        return normalizado.strip("_") or "desconhecido"

    @staticmethod
    def _preco_valido(
        valor,
    ) -> bool:
        if isinstance(
            valor,
            bool,
        ):
            return False

        if not isinstance(
            valor,
            (
                int,
                float,
            ),
        ):
            return False

        return float(valor) > 0

    @staticmethod
    def _calcular_queda_percentual(
        *,
        preco_anterior: float | None,
        preco_atual: float,
    ) -> float:
        if preco_anterior is None or preco_anterior <= 0 or preco_atual >= preco_anterior:
            return 0.0

        return round(
            ((preco_anterior - preco_atual) / preco_anterior) * 100.0,
            2,
        )
