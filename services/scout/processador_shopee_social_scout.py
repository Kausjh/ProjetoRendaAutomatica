# 63.8738, -149.7525

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests

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
from services.shopee_api_service import ShopeeApiService


class ProcessadorShopeeSocialScout:
    """
    Resolve e valida produtos Shopee usando somente a API oficial.

    Nao depende de login, Chrome ou CDP.

    Uma busca so e aceita quando existe uma correspondencia
    textual forte e inequivoca. Precos com variantes diferentes
    nao sao promovidos a preco confirmado.
    """

    MARKETPLACE = "shopee"

    TIMEOUT_REDIRECT_SEGUNDOS = 10.0

    def __init__(
        self,
        service: ShopeeApiService | None = None,
    ) -> None:
        self.service = service or ShopeeApiService()

        self._produtos_resolvidos: dict[
            str,
            dict[str, Any],
        ] = {}

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
                motivo="marketplace_nao_e_shopee",
            )

        links = self._links_shopee(
            mensagem,
            deteccao,
        )

        if not links:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo="mensagem_shopee_sem_link",
            )

        try:
            identidade, motivo_identidade = self._resolver_identidade_link(links[0])

        except requests.RequestException:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="erro",
                marketplace=self.MARKETPLACE,
                motivo="falha_resolucao_link_shopee",
            )

        if identidade is None:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo=motivo_identidade,
            )

        shop_id, item_id = identidade

        try:
            produto = self.service.buscar_produto_por_id(
                item_id=item_id,
                shop_id=shop_id,
            )

        except Exception:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="erro",
                marketplace=self.MARKETPLACE,
                motivo="falha_api_shopee_resolucao",
            )

        if produto is None:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo="produto_shopee_nao_encontrado_na_api",
            )

        item_api = self._identificador(produto.get("itemId"))

        shop_api = self._identificador(produto.get("shopId"))

        if item_api != item_id or shop_api != shop_id:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="erro",
                marketplace=self.MARKETPLACE,
                motivo=("api_shopee_retornou_" "identidade_divergente"),
            )

        link_oficial = self._link_produto(produto.get("productLink"))

        if not link_oficial:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo="produto_shopee_sem_link_oficial",
            )

        self._produtos_resolvidos[id_externo] = produto

        return ResultadoResolucaoSocialScout(
            fonte=mensagem.fonte,
            id_externo=id_externo,
            status="resolvido",
            marketplace=self.MARKETPLACE,
            tipo_destino="produto",
            url_original=links[0],
            url_destino=link_oficial,
            id_produto=item_id,
            id_anuncio=item_id,
            motivo="produto_shopee_identificado_por_id_exato",
        )

    def validar(
        self,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
    ) -> ResultadoValidacaoPrecoSocialScout:
        if resolucao.status != "resolvido" or resolucao.marketplace != self.MARKETPLACE:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                status="rejeitado",
                motivo="produto_shopee_nao_resolvido",
            )

        produto = self._produtos_resolvidos.pop(
            resolucao.id_externo,
            None,
        )

        if produto is None or self._identificador(produto.get("itemId")) != resolucao.id_produto:
            try:
                produto = self._rebuscar_por_id(
                    deteccao,
                    resolucao.id_produto,
                )

            except Exception:
                return self._resultado_validacao(
                    deteccao=deteccao,
                    resolucao=resolucao,
                    status="erro",
                    motivo="falha_api_shopee_validacao",
                )

        if produto is None:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                status="erro",
                motivo="produto_shopee_sumiu_da_api",
            )

        preco_min = self._numero(produto.get("priceMin"))

        preco_max = self._numero(produto.get("priceMax"))

        if preco_min is None or preco_min <= 0:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                produto=produto,
                status="nao_verificavel",
                motivo="preco_shopee_oficial_invalido",
            )

        if (
            preco_max is not None
            and preco_max > 0
            and not self._precos_equivalentes(
                preco_min,
                preco_max,
            )
        ):
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                produto=produto,
                status="nao_verificavel",
                motivo="produto_shopee_com_variantes_de_preco",
            )

        preco_grupo = self._numero(deteccao.preco_oferta)

        if preco_grupo is None:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                produto=produto,
                status="nao_verificavel",
                motivo="mensagem_shopee_sem_preco_base",
            )

        confere = self._precos_equivalentes(
            preco_grupo,
            preco_min,
        )

        if not confere:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                produto=produto,
                status="rejeitado",
                preco_base_confere=False,
                motivo="preco_base_shopee_divergente",
            )

        return self._resultado_validacao(
            deteccao=deteccao,
            resolucao=resolucao,
            produto=produto,
            status="validado",
            preco_base_confere=True,
            motivo="preco_shopee_confirmado_por_api",
        )

    def _rebuscar_por_id(
        self,
        deteccao: ResultadoDeteccaoSocialScout,
        item_id: str | None,
    ) -> dict[str, Any] | None:
        del deteccao

        item_id = self._identificador(item_id)

        if not item_id:
            return None

        produto = self.service.buscar_produto_por_id(
            item_id=item_id,
        )

        if produto is None:
            return None

        if self._identificador(produto.get("itemId")) != item_id:
            return None

        return produto

    def _resultado_validacao(
        self,
        *,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
        status: str,
        motivo: str,
        produto: dict[str, Any] | None = None,
        preco_base_confere: bool = False,
    ) -> ResultadoValidacaoPrecoSocialScout:
        produto = produto or {}

        return ResultadoValidacaoPrecoSocialScout(
            status=status,
            marketplace=self.MARKETPLACE,
            url=resolucao.url_destino,
            titulo_oficial=str(produto.get("productName") or "").strip(),
            preco_oficial=self._numero(produto.get("priceMin")),
            preco_original_oficial=None,
            tipo_preco_oficial="shopee_api_price_min",
            disponivel=None,
            preco_original_grupo=deteccao.preco_original,
            preco_oferta_grupo=deteccao.preco_oferta,
            preco_final_grupo=deteccao.preco_final,
            codigo_cupom=deteccao.codigo_cupom,
            desconto_cupom_percentual=(deteccao.desconto_cupom_percentual),
            preco_base_confere=preco_base_confere,
            preco_original_confere=None,
            preco_final_coerente_com_desconto=None,
            cupom_validado=False,
            motivo=motivo,
        )

    def _resolver_identidade_link(
        self,
        link: str,
    ) -> tuple[
        tuple[str, str] | None,
        str,
    ]:
        identidades = self._extrair_identidades(link)

        if len(identidades) == 1:
            return (
                next(iter(identidades)),
                "identidade_shopee_url_direta",
            )

        if len(identidades) > 1:
            return (
                None,
                "shopee_identidade_ambigua",
            )

        resposta = requests.get(
            link,
            allow_redirects=True,
            timeout=self.TIMEOUT_REDIRECT_SEGUNDOS,
            headers={"User-Agent": ("Mozilla/5.0 " "(Windows NT 10.0; Win64; x64)")},
        )

        try:
            resposta.raise_for_status()

            candidatos: set[tuple[str, str]] = set()

            for hop in resposta.history:
                candidatos.update(self._extrair_identidades(hop.url))

                location = hop.headers.get("Location")

                if location:
                    candidatos.update(
                        self._extrair_identidades(
                            urljoin(
                                hop.url,
                                location,
                            )
                        )
                    )

            candidatos.update(self._extrair_identidades(resposta.url))

        finally:
            resposta.close()

        if len(candidatos) == 1:
            return (
                next(iter(candidatos)),
                "identidade_shopee_redirect",
            )

        if len(candidatos) > 1:
            return (
                None,
                "shopee_identidade_ambigua",
            )

        return (
            None,
            "shopee_identidade_nao_resolvida",
        )

    @classmethod
    def _extrair_identidades(
        cls,
        valor: object,
    ) -> set[tuple[str, str]]:
        atual = str(valor if valor is not None else "")

        encontrados: set[tuple[str, str]] = set()

        for _ in range(5):
            for padrao in (
                r"/product/(\d+)/(\d+)",
                r"-i\.(\d+)\.(\d+)",
                r"/opaanlp/(\d+)/(\d+)",
            ):
                for match in re.finditer(
                    padrao,
                    atual,
                    flags=re.IGNORECASE,
                ):
                    encontrados.add(
                        (
                            match.group(1),
                            match.group(2),
                        )
                    )

            try:
                parsed = urlparse(atual)

                parametros = {
                    chave.casefold(): valores for chave, valores in parse_qs(parsed.query).items()
                }

                shop = next(
                    (
                        valores[0]
                        for chave, valores in parametros.items()
                        if chave
                        in {
                            "shopid",
                            "shop_id",
                        }
                        and valores
                        and str(valores[0]).isdigit()
                    ),
                    None,
                )

                item = next(
                    (
                        valores[0]
                        for chave, valores in parametros.items()
                        if chave
                        in {
                            "itemid",
                            "item_id",
                        }
                        and valores
                        and str(valores[0]).isdigit()
                    ),
                    None,
                )

                if shop and item:
                    encontrados.add(
                        (
                            str(shop),
                            str(item),
                        )
                    )

            except ValueError:
                pass

            novo = unquote(atual)

            if novo == atual:
                break

            atual = novo

        return encontrados

    @classmethod
    def _links_shopee(
        cls,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout,
    ) -> list[str]:
        resultado = []
        vistos = set()

        for valor in (
            *deteccao.links,
            *mensagem.links,
        ):
            link = str(valor or "").strip()

            if not link:
                continue

            try:
                host = (urlparse(link).hostname or "").casefold()

            except ValueError:
                continue

            if not (host == "shopee.com.br" or host.endswith(".shopee.com.br")):
                continue

            if link in vistos:
                continue

            vistos.add(link)

            resultado.append(link)

        return resultado

    @staticmethod
    def _identificador(
        valor: object,
    ) -> str | None:
        texto = str(valor if valor is not None else "").strip()

        return texto or None

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

    @staticmethod
    def _precos_equivalentes(
        primeiro: float,
        segundo: float,
    ) -> bool:
        tolerancia = max(
            1.0,
            min(
                primeiro,
                segundo,
            )
            * 0.01,
        )

        return abs(primeiro - segundo) <= tolerancia

    @staticmethod
    def _link_produto(
        valor: object,
    ) -> str | None:
        link = str(valor if valor is not None else "").strip()

        if not link:
            return None

        try:
            parsed = urlparse(link)

        except ValueError:
            return None

        host = (parsed.hostname or "").casefold()

        if not (host == "shopee.com.br" or host.endswith(".shopee.com.br")):
            return None

        return parsed._replace(
            fragment="",
        ).geturl()

    @classmethod
    def _link_original(
        cls,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout,
    ) -> str | None:
        for link in (
            *deteccao.links,
            *mensagem.links,
        ):
            if cls._link_produto(link):
                return str(link).strip()

        return None

    @staticmethod
    def _id_externo(
        mensagem: MensagemSocialScout,
    ) -> str:
        return f"{mensagem.chat_id}:" f"{mensagem.message_id}"
