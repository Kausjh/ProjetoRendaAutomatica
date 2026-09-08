# 63.8738, -149.7525

from __future__ import annotations

from models.oferta import Oferta
from models.resultado_construcao_oferta_social_scout import (
    ResultadoConstrucaoOfertaSocialScout,
)
from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from models.resultado_validacao_preco_social_scout import (
    ResultadoValidacaoPrecoSocialScout,
)


class ConstrutorOfertaSocialScout:
    """
    Converte um sinal Social Scout validado em uma Oferta
    normal do ProjetoRendaAutomatica.

    Regra fundamental:

    Oferta.preco sempre recebe o preco oficial confirmado
    no marketplace.

    Precos condicionais informados por grupos, como cupons,
    ficam apenas como metadados do resultado desta camada
    enquanto nao existir uma politica explicita para eles.
    """

    STATUS_CRIADA = "criada"
    STATUS_REJEITADA = "rejeitada"

    MARKETPLACE_MERCADO_LIVRE = "mercado_livre"
    MARKETPLACE_SHOPEE = "shopee"
    MARKETPLACE_ALIEXPRESS = "aliexpress"
    MARKETPLACE_KABUM = "kabum"

    LOJAS_POR_MARKETPLACE = {
        MARKETPLACE_MERCADO_LIVRE: "Mercado Livre",
        MARKETPLACE_SHOPEE: "Shopee",
        MARKETPLACE_ALIEXPRESS: "AliExpress",
        MARKETPLACE_KABUM: "KaBuM!",
    }

    def construir(
        self,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
        validacao: ResultadoValidacaoPrecoSocialScout,
    ) -> ResultadoConstrucaoOfertaSocialScout:
        if deteccao.classificacao != "oferta_produto":
            return self._rejeitar(
                deteccao=deteccao,
                validacao=validacao,
                motivo="deteccao_nao_e_oferta_de_produto",
            )

        if (
            resolucao.status != "resolvido"
            or resolucao.marketplace != deteccao.marketplace
            or resolucao.marketplace not in self.LOJAS_POR_MARKETPLACE
        ):
            return self._rejeitar(
                deteccao=deteccao,
                validacao=validacao,
                motivo="produto_social_nao_resolvido",
            )

        if (
            validacao.status != "validado"
            or validacao.marketplace != deteccao.marketplace
            or validacao.marketplace not in self.LOJAS_POR_MARKETPLACE
        ):
            return self._rejeitar(
                deteccao=deteccao,
                validacao=validacao,
                motivo="preco_social_nao_validado",
            )

        if validacao.disponivel is False:
            return self._rejeitar(
                deteccao=deteccao,
                validacao=validacao,
                motivo="produto_social_indisponivel",
            )

        preco = self._preco_positivo(validacao.preco_oficial)

        if preco is None:
            return self._rejeitar(
                deteccao=deteccao,
                validacao=validacao,
                motivo="preco_oficial_invalido",
            )

        link = str(resolucao.url_destino or validacao.url or "").strip()

        if not link:
            return self._rejeitar(
                deteccao=deteccao,
                validacao=validacao,
                motivo="url_oficial_ausente",
            )

        nome = str(validacao.titulo_oficial or deteccao.titulo or "").strip()

        if not nome:
            return self._rejeitar(
                deteccao=deteccao,
                validacao=validacao,
                motivo="titulo_oficial_ausente",
            )

        preco_antigo = self._preco_positivo(validacao.preco_original_oficial)

        if preco_antigo is not None and preco_antigo <= preco:
            preco_antigo = None

        oferta = Oferta(
            nome=nome,
            loja=self.LOJAS_POR_MARKETPLACE[deteccao.marketplace],
            preco=preco,
            preco_antigo=preco_antigo,
            link=link,
            imagem=None,
            moeda="R$",
            marketplace=deteccao.marketplace,
            id_produto=resolucao.id_produto,
            id_anuncio=resolucao.id_anuncio,
        )

        return ResultadoConstrucaoOfertaSocialScout(
            status=self.STATUS_CRIADA,
            oferta=oferta,
            codigo_cupom=validacao.codigo_cupom,
            preco_condicional_grupo=(validacao.preco_final_grupo),
            cupom_validado=validacao.cupom_validado,
            motivo="oferta_criada_com_preco_oficial",
        )

    @staticmethod
    def _preco_positivo(
        valor: float | None,
    ) -> float | None:
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

    def _rejeitar(
        self,
        *,
        deteccao: ResultadoDeteccaoSocialScout,
        validacao: ResultadoValidacaoPrecoSocialScout,
        motivo: str,
    ) -> ResultadoConstrucaoOfertaSocialScout:
        return ResultadoConstrucaoOfertaSocialScout(
            status=self.STATUS_REJEITADA,
            oferta=None,
            codigo_cupom=(validacao.codigo_cupom or deteccao.codigo_cupom),
            preco_condicional_grupo=(
                validacao.preco_final_grupo
                if validacao.preco_final_grupo is not None
                else deteccao.preco_final
            ),
            cupom_validado=validacao.cupom_validado,
            motivo=motivo,
        )
