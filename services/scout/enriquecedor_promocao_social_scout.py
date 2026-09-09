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
from services.scout.promotion_engine_ml import (
    PromotionEngineMercadoLivre,
)


class EnriquecedorPromocaoSocialScout:
    """Acrescenta evidencia promocional oficial ao Social Scout.

    Ordem esperada:

    validacao do marketplace
        -> PoliticaPrecoSocialScout
        -> EnriquecedorPromocaoSocialScout
        -> verificacao de status
        -> construcao da Oferta

    Nao valida codigo de cupom social.
    """

    MARKETPLACE = "mercado_livre"

    def __init__(
        self,
        promotion_engine=None,
    ) -> None:
        self.promotion_engine = promotion_engine or PromotionEngineMercadoLivre()

    def aplicar(
        self,
        *,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
        validacao: ResultadoValidacaoPrecoSocialScout,
    ) -> ResultadoValidacaoPrecoSocialScout:
        # So enriquece algo que, DEPOIS da Politica V12,
        # realmente esta liberado para continuar no fluxo.
        if validacao.status != "validado":
            return validacao

        marketplace = (
            str(validacao.marketplace or resolucao.marketplace or deteccao.marketplace or "")
            .strip()
            .casefold()
        )

        if marketplace != self.MARKETPLACE:
            return validacao

        # Sem indicio promocional social nao precisamos
        # consultar o Promotion Engine.
        if not deteccao.codigo_cupom and deteccao.preco_final is None:
            return validacao

        id_produto = str(resolucao.id_produto or "").strip()

        url_fonte = str(resolucao.url_original or resolucao.url_destino or "").strip()

        if not id_produto:
            return replace(
                validacao,
                status_promocao_marketplace=("nao_consultada"),
                motivo_promocao_marketplace=("id_produto_ausente_para_" "promotion_engine"),
            )

        if not url_fonte:
            return replace(
                validacao,
                status_promocao_marketplace=("nao_consultada"),
                motivo_promocao_marketplace=("url_fonte_ausente_para_" "promotion_engine"),
            )

        try:
            promocao = self.promotion_engine.inspecionar(
                url_fonte=url_fonte,
                id_produto=id_produto,
                preco_oficial=(validacao.preco_oficial),
                preco_final_grupo=(validacao.preco_final_grupo),
            )

        except Exception as erro:
            # O enriquecimento promocional nunca deve
            # destruir uma validacao oficial ja aprovada.
            return replace(
                validacao,
                status_promocao_marketplace="erro",
                motivo_promocao_marketplace=("falha_promotion_engine:" f"{type(erro).__name__}"),
            )

        finally:
            # fechar_engine_apos_inspecao
            #
            # O Promotion Engine usa a API Sync do
            # Playwright. Manter seu driver ativo entre
            # mensagens impede que o validador ML abra
            # uma nova sessao Sync no mesmo processo.
            #
            # Fechamos somente o driver deste engine;
            # PromotionEngine.fechar() NAO fecha o
            # Chrome compartilhado via CDP.
            fechar = getattr(
                self.promotion_engine,
                "fechar",
                None,
            )

            if callable(fechar):
                try:
                    fechar()

                except Exception:
                    # Falha de cleanup nunca deve apagar
                    # uma validacao/promocao ja obtida.
                    pass

        return replace(
            validacao,
            status_promocao_marketplace=(promocao.status),
            promocao_marketplace_confirmada=(promocao.promocao_confirmada),
            tipo_promocao_marketplace=(promocao.tipo_promocao),
            preco_promocional_marketplace=(promocao.preco_promocional),
            valor_desconto_promocional_marketplace=(promocao.valor_desconto),
            desconto_promocional_marketplace_percentual=(promocao.desconto_percentual),
            preco_grupo_confere_promocao=(promocao.preco_grupo_confere),
            fonte_promocao_marketplace=(promocao.fonte_url),
            motivo_promocao_marketplace=(promocao.motivo),
            # DELIBERADO:
            # cupom_validado permanece exatamente
            # como estava antes do Promotion Engine.
        )
