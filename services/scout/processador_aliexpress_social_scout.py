# 63.8738, -149.7525

from __future__ import annotations

import re
import urllib.request
from collections.abc import Callable
from urllib.parse import urlsplit

from models.mensagem_social_scout import MensagemSocialScout
from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from models.resultado_validacao_preco_social_scout import (
    ResultadoValidacaoPrecoSocialScout,
)
from services.aliexpress_preco_cdp_service import (
    AliExpressPrecoCdpService,
)
from services.validador_preco_aliexpress import (
    ResultadoPrecoAliExpress,
)


class ProcessadorAliExpressSocialScout:
    MARKETPLACE = "aliexpress"
    HOST_CURTO = "s.click.aliexpress.com"

    URL_CANONICA = "https://pt.aliexpress.com/" "item/{produto_id}.html"

    PADRAO_PRODUTO = re.compile(
        r"/item/(\d+)\.html(?:/|$)",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        service: AliExpressPrecoCdpService | None = None,
        resolver_url: Callable[[str], str] | None = None,
    ) -> None:
        self.service = (
            service
            if service is not None
            else AliExpressPrecoCdpService(
                arquivo_cooldown=(AliExpressPrecoCdpService.ARQUIVO_COOLDOWN_PADRAO)
            )
        )

        self.resolver_url = resolver_url or self._resolver_url_padrao

    def resolver(
        self,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout,
    ) -> ResultadoResolucaoSocialScout:
        id_externo = self._id_externo(mensagem)

        if deteccao.marketplace != self.MARKETPLACE:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=deteccao.marketplace,
                motivo="marketplace_nao_e_aliexpress",
            )

        links = self._links_aliexpress(
            mensagem,
            deteccao,
        )

        if not links:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo="mensagem_aliexpress_sem_link",
            )

        identidades: dict[str, str] = {}
        houve_erro = False

        for link in links:
            destino = link

            produto_id = self._produto_id_url(destino)

            if produto_id is None and self._host(link) == self.HOST_CURTO:
                try:
                    destino = self.resolver_url(link)

                except Exception:
                    houve_erro = True
                    continue

                produto_id = self._produto_id_url(destino)

            if produto_id is None:
                continue

            identidades.setdefault(
                produto_id,
                link,
            )

        if houve_erro:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="erro",
                marketplace=self.MARKETPLACE,
                motivo="falha_resolucao_link_aliexpress",
            )

        if len(identidades) > 1:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo="aliexpress_identidade_ambigua",
            )

        if not identidades:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo="aliexpress_destino_nao_e_produto",
            )

        produto_id, link_origem = next(iter(identidades.items()))

        url_canonica = self.URL_CANONICA.format(produto_id=produto_id)

        return ResultadoResolucaoSocialScout(
            fonte=mensagem.fonte,
            id_externo=id_externo,
            status="resolvido",
            marketplace=self.MARKETPLACE,
            tipo_destino="produto",
            url_original=link_origem,
            url_destino=url_canonica,
            id_produto=produto_id,
            id_anuncio=produto_id,
            motivo=("produto_aliexpress_" "identificado_por_id_exato"),
        )

    def validar(
        self,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
    ) -> ResultadoValidacaoPrecoSocialScout:
        if (
            resolucao.status != "resolvido"
            or resolucao.marketplace != self.MARKETPLACE
            or not resolucao.id_produto
        ):
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                status="rejeitado",
                motivo="produto_aliexpress_nao_resolvido",
            )

        try:
            resultados = self.service.validar_produtos(
                [
                    resolucao.id_produto,
                ]
            )

        except Exception:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                status="erro",
                motivo="falha_validacao_aliexpress",
            )

        resultado = resultados.get(resolucao.id_produto)

        if resultado is None:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                status="erro",
                motivo="aliexpress_sem_resultado_validacao",
            )

        if not resultado.valido or resultado.preco is None:
            status = "erro" if self._motivo_transitorio(resultado.motivo) else "nao_verificavel"

            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                resultado=resultado,
                status=status,
                motivo=resultado.motivo,
            )

        preco_oficial = self._numero(resultado.preco)

        if preco_oficial is None:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                resultado=resultado,
                status="nao_verificavel",
                motivo="preco_aliexpress_oficial_invalido",
            )

        preco_grupo = self._numero(deteccao.preco_oferta)

        if preco_grupo is None:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                resultado=resultado,
                status="nao_verificavel",
                motivo="mensagem_aliexpress_sem_preco_base",
            )

        confere = self._precos_equivalentes(
            preco_grupo,
            preco_oficial,
        )

        if not confere:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                resultado=resultado,
                status="rejeitado",
                preco_base_confere=False,
                motivo="preco_base_aliexpress_divergente",
            )

        return self._resultado_validacao(
            deteccao=deteccao,
            resolucao=resolucao,
            resultado=resultado,
            status="validado",
            preco_base_confere=True,
            motivo="preco_aliexpress_confirmado_por_pdp",
        )

    def _resultado_validacao(
        self,
        *,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
        status: str,
        motivo: str,
        resultado: ResultadoPrecoAliExpress | None = None,
        preco_base_confere: bool = False,
    ) -> ResultadoValidacaoPrecoSocialScout:
        preco_oficial = None
        preco_original = None
        disponivel = None

        if resultado is not None:
            preco_oficial = self._numero(resultado.preco)

            preco_original = self._numero(resultado.preco_normal)

            if resultado.valido:
                disponivel = True

        if (
            preco_original is not None
            and preco_oficial is not None
            and preco_original <= preco_oficial
        ):
            preco_original = None

        return ResultadoValidacaoPrecoSocialScout(
            status=status,
            marketplace=self.MARKETPLACE,
            url=resolucao.url_destino,
            titulo_oficial="",
            preco_oficial=preco_oficial,
            preco_original_oficial=preco_original,
            tipo_preco_oficial=("aliexpress_pdp_brl" if preco_oficial is not None else None),
            disponivel=disponivel,
            preco_original_grupo=deteccao.preco_original,
            preco_oferta_grupo=deteccao.preco_oferta,
            preco_final_grupo=deteccao.preco_final,
            codigo_cupom=deteccao.codigo_cupom,
            desconto_cupom_percentual=(deteccao.desconto_cupom_percentual),
            preco_base_confere=preco_base_confere,
            cupom_validado=False,
            motivo=motivo,
        )

    def _motivo_transitorio(
        self,
        motivo: str | None,
    ) -> bool:
        texto = str(motivo or "").strip()

        if texto in {
            self.service.MOTIVO_DESAFIO,
            self.service.MOTIVO_COOLDOWN,
        }:
            return True

        return texto.casefold().startswith("erro ")

    @classmethod
    def _links_aliexpress(
        cls,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout,
    ) -> tuple[str, ...]:
        encontrados: list[str] = []

        for bruto in (
            *mensagem.links,
            *deteccao.links,
        ):
            link = str(bruto or "").strip()

            if not link:
                continue

            if not cls._host_aliexpress(cls._host(link)):
                continue

            if link not in encontrados:
                encontrados.append(link)

        return tuple(encontrados)

    @classmethod
    def _produto_id_url(
        cls,
        url: str,
    ) -> str | None:
        try:
            partes = urlsplit(str(url or ""))

        except ValueError:
            return None

        if not cls._host_aliexpress(partes.hostname or ""):
            return None

        correspondencia = cls.PADRAO_PRODUTO.search(partes.path)

        if not correspondencia:
            return None

        return correspondencia.group(1)

    @staticmethod
    def _host(
        url: str,
    ) -> str:
        try:
            return (urlsplit(str(url or "")).hostname or "").casefold()

        except ValueError:
            return ""

    @staticmethod
    def _host_aliexpress(
        host: str,
    ) -> bool:
        host = str(host or "").casefold()

        return host == "aliexpress.com" or host.endswith(".aliexpress.com")

    @staticmethod
    def _numero(
        valor: object,
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

    @classmethod
    def _precos_equivalentes(
        cls,
        primeiro: object,
        segundo: object,
    ) -> bool:
        a = cls._numero(primeiro)

        b = cls._numero(segundo)

        if a is None or b is None:
            return False

        return a == b

    @staticmethod
    def _id_externo(
        mensagem: MensagemSocialScout,
    ) -> str:
        return f"{mensagem.chat_id}:" f"{mensagem.message_id}"

    @staticmethod
    def _resolver_url_padrao(
        link: str,
    ) -> str:
        requisicao = urllib.request.Request(
            str(link),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "Chrome/150 Safari/537.36"
                ),
            },
            method="GET",
        )

        with urllib.request.urlopen(
            requisicao,
            timeout=15,
        ) as resposta:
            return str(resposta.geturl())
