# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import replace

from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from models.resultado_validacao_preco_social_scout import (
    ResultadoValidacaoPrecoSocialScout,
)


class PoliticaPrecoSocialScout:
    """
    Politica V12: o preco social e sinal de descoberta.

    A fonte de verdade do preco continua sendo a loja/API oficial.

    Esta politica NAO recupera:
    - produto nao resolvido;
    - marketplace divergente;
    - produto indisponivel;
    - preco oficial ausente;
    - titulo divergente;
    - variantes ambiguas;
    - marketplace sem suporte.

    Ela somente impede que um produto oficialmente identificado
    e precificado seja descartado porque o preco informado pelo
    grupo estava ausente, condicionado ou divergente.
    """

    MARKETPLACES = frozenset(
        {
            "mercado_livre",
            "shopee",
        }
    )

    MOTIVOS_RECUPERAVEIS = frozenset(
        {
            "mensagem_social_sem_preco_base",
            "precos_da_fonte_divergem_dos_dados_oficiais",
            "mensagem_shopee_sem_preco_base",
            "preco_base_shopee_divergente",
        }
    )

    MOTIVO_OFICIAL = "preco_oficial_confirmado_" "preco_social_apenas_sinal"

    def aplicar(
        self,
        *,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
        validacao: ResultadoValidacaoPrecoSocialScout,
    ) -> ResultadoValidacaoPrecoSocialScout:
        if validacao.status == "validado":
            return validacao

        motivo = str(validacao.motivo or "").strip()

        if motivo not in self.MOTIVOS_RECUPERAVEIS:
            return validacao

        if resolucao.status != "resolvido":
            return validacao

        if resolucao.tipo_destino not in {
            None,
            "produto",
        }:
            return validacao

        marketplaces = {
            str(valor).strip()
            for valor in (
                deteccao.marketplace,
                resolucao.marketplace,
                validacao.marketplace,
            )
            if str(valor or "").strip()
        }

        if len(marketplaces) != 1:
            return validacao

        marketplace = next(iter(marketplaces))

        if marketplace not in self.MARKETPLACES:
            return validacao

        preco_oficial = self._numero_positivo(validacao.preco_oficial)

        if preco_oficial is None:
            return validacao

        if validacao.disponivel is False:
            return validacao

        alteracoes = {
            "status": "validado",
            "preco_base_confere": False,
            "motivo": (f"{self.MOTIVO_OFICIAL}:" f"{motivo}"),
        }

        # Mantemos explicitamente qualquer cupom social
        # como NAO validado.
        if hasattr(
            validacao,
            "cupom_validado",
        ):
            alteracoes["cupom_validado"] = False

        return replace(
            validacao,
            **alteracoes,
        )

    @staticmethod
    def _numero_positivo(
        valor,
    ) -> float | None:
        try:
            numero = float(valor)

        except (
            TypeError,
            ValueError,
        ):
            return None

        if numero <= 0:
            return None

        return numero
