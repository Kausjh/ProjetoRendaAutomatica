# 63.8738, -149.7525

from __future__ import annotations

import re
import urllib.request
from urllib.parse import urlsplit

from models.mensagem_social_scout import (
    MensagemSocialScout,
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
from services.kabum_preco_cdp_service import (
    KabumPrecoCdpService,
    ResultadoPrecoKabum,
)


class ProcessadorKabumSocialScout:
    MARKETPLACE = "kabum"
    HOST_TIDDLY = "tidd.ly"

    PADRAO_PRODUTO = re.compile(
        r"/produto/(\d+)(?:/|$)",
        flags=re.IGNORECASE,
    )

    def __init__(
        self,
        service: KabumPrecoCdpService | None = None,
        resolver_url=None,
    ) -> None:
        self.service = service if service is not None else KabumPrecoCdpService()

        self.resolver_url = resolver_url or self._resolver_url_padrao

    @classmethod
    def tem_link_tiddly(
        cls,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout,
    ) -> bool:
        return any(
            cls._host(link) == cls.HOST_TIDDLY
            for link in (
                *mensagem.links,
                *deteccao.links,
            )
        )

    def resolver(
        self,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout,
    ) -> ResultadoResolucaoSocialScout:
        id_externo = self._id_externo(mensagem)

        if deteccao.marketplace not in {
            None,
            self.MARKETPLACE,
        }:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=deteccao.marketplace,
                motivo="marketplace_nao_e_kabum",
            )

        links = self._links_relevantes(
            mensagem,
            deteccao,
        )

        if not links:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo="mensagem_kabum_sem_link",
            )

        produtos: dict[
            str,
            tuple[str, str],
        ] = {}

        houve_erro = False
        houve_outro_host = False

        for link in links:
            destino = link

            if self._host(link) == self.HOST_TIDDLY:
                try:
                    destino = self.resolver_url(link)

                except Exception:
                    houve_erro = True
                    continue

                if not self._host_kabum(self._host(destino)):
                    houve_outro_host = True
                    continue

            produto_id = self._produto_id_url(destino)

            if produto_id is None:
                continue

            produtos.setdefault(
                produto_id,
                (
                    link,
                    self._limpar_url(destino),
                ),
            )

        if houve_erro:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="erro",
                marketplace=self.MARKETPLACE,
                motivo=("falha_resolucao_link_kabum"),
            )

        if len(produtos) > 1:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo="kabum_identidade_ambigua",
            )

        if produtos and houve_outro_host:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo="tiddly_destino_misto",
            )

        if not produtos:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status="nao_suportado",
                marketplace=self.MARKETPLACE,
                motivo=("kabum_destino_nao_e_produto"),
            )

        produto_id, (
            url_original,
            url_destino,
        ) = next(iter(produtos.items()))

        return ResultadoResolucaoSocialScout(
            fonte=mensagem.fonte,
            id_externo=id_externo,
            status="resolvido",
            marketplace=self.MARKETPLACE,
            tipo_destino="produto",
            url_original=url_original,
            url_destino=url_destino,
            id_produto=produto_id,
            motivo=("produto_kabum_" "identificado_por_id_exato"),
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
                motivo=("produto_kabum_nao_resolvido"),
            )

        try:
            resultado = self.service.validar(
                resolucao.id_produto,
                resolucao.url_destino,
            )

        except Exception:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                status="erro",
                motivo="falha_validacao_kabum",
            )

        if not resultado.valido:
            status = (
                "erro"
                if str(resultado.motivo or "").startswith("erro_kabum_")
                else "nao_verificavel"
            )

            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                resultado=resultado,
                status=status,
                motivo=resultado.motivo,
            )

        if resultado.disponivel is False:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                resultado=resultado,
                status="nao_verificavel",
                motivo=("produto_kabum_indisponivel"),
            )

        preco_oficial = self._numero(resultado.preco_brl)

        if preco_oficial is None:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                resultado=resultado,
                status="nao_verificavel",
                motivo=("preco_kabum_oficial_invalido"),
            )

        preco_grupo = self._numero(deteccao.preco_oferta)

        if preco_grupo is None:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                resultado=resultado,
                status="nao_verificavel",
                motivo=("mensagem_kabum_sem_preco_base"),
            )

        if preco_grupo != preco_oficial:
            return self._resultado_validacao(
                deteccao=deteccao,
                resolucao=resolucao,
                resultado=resultado,
                status="rejeitado",
                preco_base_confere=False,
                motivo=("preco_base_kabum_divergente"),
            )

        return self._resultado_validacao(
            deteccao=deteccao,
            resolucao=resolucao,
            resultado=resultado,
            status="validado",
            preco_base_confere=True,
            motivo=("preco_kabum_confirmado_por_pdp"),
        )

    def _resultado_validacao(
        self,
        *,
        deteccao: ResultadoDeteccaoSocialScout,
        resolucao: ResultadoResolucaoSocialScout,
        status: str,
        motivo: str,
        resultado: ResultadoPrecoKabum | None = None,
        preco_base_confere: bool = False,
    ) -> ResultadoValidacaoPrecoSocialScout:
        resultado = resultado or ResultadoPrecoKabum(
            produto_id=str(resolucao.id_produto or ""),
            valido=False,
            motivo=motivo,
        )

        return ResultadoValidacaoPrecoSocialScout(
            status=status,
            marketplace=self.MARKETPLACE,
            url=(resultado.url_produto or resolucao.url_destino),
            titulo_oficial=resultado.titulo,
            preco_oficial=self._numero(resultado.preco_brl),
            preco_original_oficial=None,
            tipo_preco_oficial=("kabum_jsonld_brl" if resultado.preco_brl is not None else None),
            disponivel=resultado.disponivel,
            preco_original_grupo=(deteccao.preco_original),
            preco_oferta_grupo=(deteccao.preco_oferta),
            preco_final_grupo=(deteccao.preco_final),
            codigo_cupom=(deteccao.codigo_cupom),
            desconto_cupom_percentual=(deteccao.desconto_cupom_percentual),
            preco_base_confere=(preco_base_confere),
            cupom_validado=False,
            motivo=motivo,
        )

    @classmethod
    def _links_relevantes(
        cls,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout,
    ) -> tuple[str, ...]:
        resultado = []

        for bruto in (
            *mensagem.links,
            *deteccao.links,
        ):
            link = str(bruto or "").strip()

            if not link:
                continue

            host = cls._host(link)

            if host == cls.HOST_TIDDLY or cls._host_kabum(host):
                if link not in resultado:
                    resultado.append(link)

        return tuple(resultado)

    @classmethod
    def _produto_id_url(
        cls,
        url: str,
    ) -> str | None:
        try:
            partes = urlsplit(str(url or ""))

        except ValueError:
            return None

        if not cls._host_kabum(partes.hostname or ""):
            return None

        match = cls.PADRAO_PRODUTO.search(partes.path)

        if not match:
            return None

        return match.group(1)

    @staticmethod
    def _host(
        url: str,
    ) -> str:
        try:
            return (urlsplit(str(url or "")).hostname or "").casefold()

        except ValueError:
            return ""

    @staticmethod
    def _host_kabum(
        host: str,
    ) -> bool:
        host = str(host or "").casefold()

        return host == "kabum.com.br" or host.endswith(".kabum.com.br")

    @staticmethod
    def _limpar_url(
        url: str,
    ) -> str:
        try:
            partes = urlsplit(str(url or ""))

        except ValueError:
            return ""

        return f"{partes.scheme}://" f"{partes.netloc}" f"{partes.path}"

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
