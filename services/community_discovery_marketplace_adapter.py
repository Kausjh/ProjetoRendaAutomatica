# 63.8738, -149.7525

from __future__ import annotations

import hashlib
from dataclasses import replace

from models.community_discovery import DescobertaComunitaria
from models.mensagem_social_scout import MensagemSocialScout
from models.resultado_community_discovery_adapter import (
    ResultadoCommunityDiscoveryAdapter,
)
from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from models.resultado_validacao_preco_social_scout import (
    ResultadoValidacaoPrecoSocialScout,
)
from services.scout.construtor_oferta_social_scout import (
    ConstrutorOfertaSocialScout,
)
from services.scout.mercado_livre_catalog_api import (
    ClienteCatalogoMercadoLivre,
    ErroApiMercadoLivre,
)
from services.scout.processador_aliexpress_social_scout import (
    ProcessadorAliExpressSocialScout,
)
from services.scout.processador_kabum_social_scout import (
    ProcessadorKabumSocialScout,
)
from services.scout.processador_shopee_social_scout import (
    ProcessadorShopeeSocialScout,
)
from services.scout.social_scout_destino_resolver import (
    ResolvedorDestinoSocialScout,
)
from services.scout.validador_preco_ml_social_scout import (
    ValidadorPrecoMercadoLivreSocialScout,
)


class CommunityDiscoveryMarketplaceAdapter:
    STATUS_OFERTA_CRIADA = "oferta_criada"
    STATUS_RETRY = "retry"
    STATUS_REJEITADA = "rejeitada"
    STATUS_NAO_SUPORTADA = "nao_suportada"

    MARKETPLACE_MERCADO_LIVRE = "mercado_livre"
    MARKETPLACE_SHOPEE = "shopee"
    MARKETPLACE_ALIEXPRESS = "aliexpress"
    MARKETPLACE_KABUM = "kabum"
    MARKETPLACE_AMAZON = "amazon"

    MARKETPLACES_COM_PROCESSADOR = {
        MARKETPLACE_MERCADO_LIVRE,
        MARKETPLACE_SHOPEE,
        MARKETPLACE_ALIEXPRESS,
        MARKETPLACE_KABUM,
    }

    MOTIVOS_SEM_PRECO_OBSERVADO = {
        "mensagem_shopee_sem_preco_base",
        "mensagem_aliexpress_sem_preco_base",
        "mensagem_kabum_sem_preco_base",
    }

    def __init__(
        self,
        *,
        resolvedor_ml=None,
        validador_ml=None,
        cliente_catalogo_ml=None,
        processador_shopee=None,
        processador_aliexpress=None,
        processador_kabum=None,
        construtor=None,
    ) -> None:
        self._resolvedor_ml = resolvedor_ml
        self._validador_ml = validador_ml
        self._cliente_catalogo_ml = cliente_catalogo_ml
        self._processador_shopee = processador_shopee
        self._processador_aliexpress = processador_aliexpress
        self._processador_kabum = processador_kabum
        self._construtor = construtor

    def processar(
        self,
        descoberta: DescobertaComunitaria,
    ) -> ResultadoCommunityDiscoveryAdapter:
        if descoberta.status != "processing":
            raise ValueError("Descoberta precisa estar em processing antes do adapter.")

        marketplace = str(descoberta.marketplace or "").strip().casefold()

        if marketplace == self.MARKETPLACE_AMAZON:
            return self._resultado(
                status=self.STATUS_NAO_SUPORTADA,
                marketplace=marketplace,
                motivo="amazon_sem_processador_de_produto",
            )

        if marketplace not in self.MARKETPLACES_COM_PROCESSADOR:
            return self._resultado(
                status=self.STATUS_NAO_SUPORTADA,
                marketplace=marketplace or None,
                motivo="marketplace_comunitario_nao_suportado",
            )

        mensagem = self._criar_mensagem(descoberta)
        deteccao = self._criar_deteccao(
            descoberta,
            marketplace=marketplace,
        )

        if marketplace == self.MARKETPLACE_MERCADO_LIVRE:
            return self._processar_mercado_livre(
                marketplace=marketplace,
                mensagem=mensagem,
                deteccao=deteccao,
            )

        processador = self._obter_processador(marketplace)

        try:
            resolucao = processador.resolver(
                mensagem,
                deteccao,
            )
        except Exception as erro:
            return self._resultado(
                status=self.STATUS_RETRY,
                marketplace=marketplace,
                motivo=("erro_resolucao_" f"{marketplace}:{type(erro).__name__}"),
                transitorio=True,
            )

        erro_resolucao = self._avaliar_resolucao(
            marketplace=marketplace,
            resolucao=resolucao,
        )

        if erro_resolucao is not None:
            return erro_resolucao

        try:
            validacao = processador.validar(
                deteccao,
                resolucao,
            )
        except Exception as erro:
            return self._resultado(
                status=self.STATUS_RETRY,
                marketplace=marketplace,
                motivo=("erro_validacao_" f"{marketplace}:{type(erro).__name__}"),
                resolucao=resolucao,
                transitorio=True,
            )

        validacao = self._promover_validacao_link_only(
            validacao,
        )

        return self._construir_oferta(
            marketplace=marketplace,
            deteccao=deteccao,
            resolucao=resolucao,
            validacao=validacao,
        )

    def _processar_mercado_livre(
        self,
        *,
        marketplace: str,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout,
    ) -> ResultadoCommunityDiscoveryAdapter:
        resolvedor = self._resolvedor_ml_real()

        try:
            resolucao = resolvedor.resolver(
                mensagem,
                deteccao,
            )
        except Exception as erro:
            return self._resultado(
                status=self.STATUS_RETRY,
                marketplace=marketplace,
                motivo=("erro_resolucao_mercado_livre:" f"{type(erro).__name__}"),
                transitorio=True,
            )

        erro_resolucao = self._avaliar_resolucao(
            marketplace=marketplace,
            resolucao=resolucao,
        )

        if erro_resolucao is not None:
            return erro_resolucao

        product_id = (
            str(
                getattr(
                    resolucao,
                    "id_produto",
                    "",
                )
                or ""
            )
            .strip()
            .upper()
        )

        if not product_id:
            return self._resultado(
                status=self.STATUS_NAO_SUPORTADA,
                marketplace=marketplace,
                motivo="mercado_livre_sem_product_id_catalogo",
                resolucao=resolucao,
            )

        try:
            snapshot_api = self._cliente_catalogo_ml_real().consultar_snapshot(
                product_id,
            )
        except ErroApiMercadoLivre as erro:
            return self._resultado(
                status=self.STATUS_RETRY,
                marketplace=marketplace,
                motivo=f"erro_api_catalogo_mercado_livre:{erro.motivo}",
                resolucao=resolucao,
                transitorio=erro.transitorio,
            )
        except Exception as erro:
            return self._resultado(
                status=self.STATUS_RETRY,
                marketplace=marketplace,
                motivo=("erro_api_catalogo_mercado_livre:" f"{type(erro).__name__}"),
                resolucao=resolucao,
                transitorio=True,
            )

        if snapshot_api is None:
            return self._resultado(
                status=self.STATUS_REJEITADA,
                marketplace=marketplace,
                motivo="mercado_livre_sem_publicacao_catalogo_com_preco_valido",
                resolucao=resolucao,
            )

        snapshot = snapshot_api.como_snapshot_validacao()
        preco_oficial = float(snapshot_api.preco)

        deteccao_oficial = replace(
            deteccao,
            preco_oferta=preco_oficial,
            preco_final=preco_oficial,
        )

        validador = self._validador_ml_real()

        try:
            validacao = validador._avaliar_snapshot(
                deteccao=deteccao_oficial,
                resolucao=resolucao,
                snapshot=snapshot,
            )
        except Exception as erro:
            return self._resultado(
                status=self.STATUS_RETRY,
                marketplace=marketplace,
                motivo=("erro_avaliacao_mercado_livre:" f"{type(erro).__name__}"),
                resolucao=resolucao,
                transitorio=True,
            )

        return self._construir_oferta(
            marketplace=marketplace,
            deteccao=deteccao_oficial,
            resolucao=resolucao,
            validacao=validacao,
        )

    def _avaliar_resolucao(
        self,
        *,
        marketplace: str,
        resolucao,
    ) -> ResultadoCommunityDiscoveryAdapter | None:
        if resolucao.status == "erro":
            return self._resultado(
                status=self.STATUS_RETRY,
                marketplace=marketplace,
                motivo=(resolucao.motivo or f"erro_resolucao_{marketplace}"),
                resolucao=resolucao,
                transitorio=True,
            )

        if resolucao.status != "resolvido":
            return self._resultado(
                status=self.STATUS_REJEITADA,
                marketplace=marketplace,
                motivo=(resolucao.motivo or f"produto_{marketplace}_nao_resolvido"),
                resolucao=resolucao,
            )

        return None

    def _promover_validacao_link_only(
        self,
        validacao: ResultadoValidacaoPrecoSocialScout,
    ) -> ResultadoValidacaoPrecoSocialScout:
        if validacao.status == "validado":
            return validacao

        if validacao.motivo not in self.MOTIVOS_SEM_PRECO_OBSERVADO:
            return validacao

        try:
            preco = float(validacao.preco_oficial)
        except (TypeError, ValueError):
            return validacao

        if preco <= 0:
            return validacao

        if validacao.disponivel is False:
            return validacao

        marketplace = str(validacao.marketplace or "").strip().casefold()

        return replace(
            validacao,
            status="validado",
            preco_base_confere=True,
            motivo=("preco_oficial_confirmado_sem_preco_observado:" + marketplace),
        )

    def _construir_oferta(
        self,
        *,
        marketplace: str,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao,
        validacao: ResultadoValidacaoPrecoSocialScout,
    ) -> ResultadoCommunityDiscoveryAdapter:
        if validacao.status == "erro":
            return self._resultado(
                status=self.STATUS_RETRY,
                marketplace=marketplace,
                motivo=(validacao.motivo or f"erro_validacao_{marketplace}"),
                resolucao=resolucao,
                validacao=validacao,
                transitorio=True,
            )

        if validacao.status != "validado":
            return self._resultado(
                status=self.STATUS_REJEITADA,
                marketplace=marketplace,
                motivo=(validacao.motivo or f"validacao_{marketplace}_nao_aprovada"),
                resolucao=resolucao,
                validacao=validacao,
            )

        if validacao.disponivel is False:
            return self._resultado(
                status=self.STATUS_REJEITADA,
                marketplace=marketplace,
                motivo=f"produto_{marketplace}_indisponivel",
                resolucao=resolucao,
                validacao=validacao,
            )

        titulo = str(validacao.titulo_oficial or deteccao.titulo or "").strip()

        if not titulo:
            return self._resultado(
                status=self.STATUS_NAO_SUPORTADA,
                marketplace=marketplace,
                motivo=("titulo_oficial_ausente_para_" "community_discovery_link_only"),
                resolucao=resolucao,
                validacao=validacao,
            )

        try:
            preco = float(validacao.preco_oficial)
        except (TypeError, ValueError):
            preco = 0.0

        if preco <= 0:
            return self._resultado(
                status=self.STATUS_REJEITADA,
                marketplace=marketplace,
                motivo=f"preco_oficial_{marketplace}_invalido",
                resolucao=resolucao,
                validacao=validacao,
            )

        construcao = self._construtor_real().construir(
            deteccao,
            resolucao,
            validacao,
        )

        if construcao.status != "criada" or construcao.oferta is None:
            return self._resultado(
                status=self.STATUS_REJEITADA,
                marketplace=marketplace,
                motivo=(construcao.motivo or "falha_construcao_oferta_comunitaria"),
                resolucao=resolucao,
                validacao=validacao,
            )

        construcao.oferta.origem_descoberta = "community_discovery"

        return self._resultado(
            status=self.STATUS_OFERTA_CRIADA,
            marketplace=marketplace,
            motivo="oferta_comunitaria_criada_com_preco_oficial",
            oferta=construcao.oferta,
            resolucao=resolucao,
            validacao=validacao,
        )

    @staticmethod
    def _criar_mensagem(
        descoberta: DescobertaComunitaria,
    ) -> MensagemSocialScout:
        digest = hashlib.sha256(descoberta.id.encode("utf-8")).hexdigest()

        message_id = (int(digest[:8], 16) % 2_147_483_646) + 1

        return MensagemSocialScout(
            fonte="community_discovery",
            chat_id=descoberta.conta_id,
            message_id=message_id,
            chat_titulo="Community Discovery",
            texto=descoberta.url_normalizada,
            links=(descoberta.url_normalizada,),
        )

    @staticmethod
    def _criar_deteccao(
        descoberta: DescobertaComunitaria,
        *,
        marketplace: str,
    ) -> ResultadoDeteccaoSocialScout:
        return ResultadoDeteccaoSocialScout(
            classificacao="oferta_produto",
            utilizavel=True,
            titulo="",
            marketplace=marketplace,
            links=(descoberta.url_normalizada,),
            motivo="community_discovery_link_only",
        )

    def _obter_processador(self, marketplace: str):
        if marketplace == self.MARKETPLACE_SHOPEE:
            if self._processador_shopee is None:
                self._processador_shopee = ProcessadorShopeeSocialScout()
            return self._processador_shopee

        if marketplace == self.MARKETPLACE_ALIEXPRESS:
            if self._processador_aliexpress is None:
                self._processador_aliexpress = ProcessadorAliExpressSocialScout()
            return self._processador_aliexpress

        if marketplace == self.MARKETPLACE_KABUM:
            if self._processador_kabum is None:
                self._processador_kabum = ProcessadorKabumSocialScout()
            return self._processador_kabum

        raise ValueError(f"Marketplace sem processador generico: {marketplace}")

    def _resolvedor_ml_real(self):
        if self._resolvedor_ml is None:
            self._resolvedor_ml = ResolvedorDestinoSocialScout()
        return self._resolvedor_ml

    def _cliente_catalogo_ml_real(self):
        if self._cliente_catalogo_ml is None:
            self._cliente_catalogo_ml = ClienteCatalogoMercadoLivre()
        return self._cliente_catalogo_ml

    def _validador_ml_real(self):
        if self._validador_ml is None:
            self._validador_ml = ValidadorPrecoMercadoLivreSocialScout()
        return self._validador_ml

    def _construtor_real(self):
        if self._construtor is None:
            self._construtor = ConstrutorOfertaSocialScout()
        return self._construtor

    @staticmethod
    def _resultado(
        *,
        status: str,
        marketplace: str | None,
        motivo: str,
        oferta=None,
        resolucao=None,
        validacao=None,
        transitorio: bool = False,
    ) -> ResultadoCommunityDiscoveryAdapter:
        return ResultadoCommunityDiscoveryAdapter(
            status=status,
            marketplace=marketplace,
            motivo=str(motivo or "").strip(),
            oferta=oferta,
            resolucao=resolucao,
            validacao=validacao,
            transitorio=bool(transitorio),
        )
