# 63.8738, -149.7525

from __future__ import annotations

import html as html_lib
import math
import re
import unicodedata
from urllib.parse import (
    parse_qsl,
    urlencode,
    urlparse,
)

import requests

from models.mensagem_social_scout import (
    MensagemSocialScout,
)
from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from services.identificador_mercado_livre import (
    IdentificadorMercadoLivre,
)
from services.scout.detector_promocao_social_scout import (
    DetectorPromocaoSocialScout,
)


class ResolvedorDestinoSocialScout:
    """
    Resolve links encontrados pelo Social Scout.

    Nesta primeira fase, somente Mercado Livre e suportado.

    Links meli.la sao tratados apenas como pistas para chegar
    ao destino oficial. Links de afiliados observados nunca sao
    reutilizados como links de publicacao.

    Quando um meli.la termina em /social/<afiliado>, somente o
    card explicitamente destacado pelo Mercado Livre e aceito.
    Recomendacoes da pagina nao sao utilizadas como destino.
    """

    MARKETPLACE_MERCADO_LIVRE = "mercado_livre"

    STATUS_RESOLVIDO = "resolvido"
    STATUS_IGNORADO = "ignorado"
    STATUS_NAO_SUPORTADO = "nao_suportado"
    STATUS_ERRO = "erro"

    PADRAO_MLB = re.compile(
        r"MLB[-_]?\d+",
        re.IGNORECASE,
    )

    PADRAO_URL_MERCADO_LIVRE = re.compile(
        r"""https://(?:www\.)?mercadolivre\.com\.br/""" r"""[^"'<>\\\s]+""",
        re.IGNORECASE,
    )

    PADRAO_META = re.compile(
        r"<meta\b[^>]*>",
        re.IGNORECASE,
    )

    PADRAO_ATRIBUTO_HTML = re.compile(
        r"""([:\w-]+)\s*=\s*(["'])(.*?)\2""",
        re.IGNORECASE | re.DOTALL,
    )

    TERMOS_GENERICOS_TITULO = {
        "produto",
        "oferta",
        "promocao",
        "promocoes",
        "desconto",
        "original",
        "novo",
        "nova",
    }

    def __init__(
        self,
        timeout_segundos: float = 15.0,
        identificador_mercado_livre: IdentificadorMercadoLivre | None = None,
    ) -> None:
        self.timeout_segundos = max(
            float(timeout_segundos),
            1.0,
        )

        self.identificador_mercado_livre = (
            identificador_mercado_livre or IdentificadorMercadoLivre()
        )

    def resolver(
        self,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout | None = None,
    ) -> ResultadoResolucaoSocialScout:
        resultado_deteccao = deteccao or DetectorPromocaoSocialScout.detectar(mensagem)

        id_externo = self._criar_id_externo(mensagem)

        if resultado_deteccao.classificacao != DetectorPromocaoSocialScout.OFERTA_PRODUTO:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status=self.STATUS_IGNORADO,
                marketplace=(resultado_deteccao.marketplace),
                motivo=("mensagem_nao_e_oferta_de_produto"),
            )

        marketplace_detectado = resultado_deteccao.marketplace

        if marketplace_detectado not in (
            None,
            self.MARKETPLACE_MERCADO_LIVRE,
        ):
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status=self.STATUS_NAO_SUPORTADO,
                marketplace=marketplace_detectado,
                motivo=("marketplace_social_ainda_nao_suportado"),
            )

        links = tuple(str(link).strip() for link in resultado_deteccao.links if str(link).strip())

        if not links:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status=self.STATUS_NAO_SUPORTADO,
                marketplace=marketplace_detectado,
                motivo="mensagem_sem_link_util",
            )

        encontrou_link_curto = False

        for link in links:
            host = self._host(link)

            if self._eh_dominio_oficial_ml(host):
                if self._eh_pagina_social(link):
                    return self._resolver_por_http(
                        mensagem=mensagem,
                        deteccao=resultado_deteccao,
                        url_original=link,
                        url_requisicao=link,
                        motivo_falha=("falha_ao_resolver_pagina_social"),
                    )

                return self._classificar_mercado_livre(
                    mensagem=mensagem,
                    url_original=link,
                    url_destino=link,
                    http_status=None,
                )

            if not self._eh_link_curto_ml(host):
                continue

            encontrou_link_curto = True

            return self._resolver_por_http(
                mensagem=mensagem,
                deteccao=resultado_deteccao,
                url_original=link,
                url_requisicao=link,
                motivo_falha=("falha_ao_resolver_link_curto"),
            )

        if encontrou_link_curto:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=id_externo,
                status=self.STATUS_ERRO,
                marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                motivo=("falha_ao_resolver_link_curto"),
            )

        return ResultadoResolucaoSocialScout(
            fonte=mensagem.fonte,
            id_externo=id_externo,
            status=self.STATUS_NAO_SUPORTADO,
            marketplace=marketplace_detectado,
            motivo=("nenhum_link_mercado_livre_suportado"),
        )

    def _resolver_por_http(
        self,
        *,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout,
        url_original: str,
        url_requisicao: str,
        motivo_falha: str,
    ) -> ResultadoResolucaoSocialScout:
        try:
            resposta = requests.get(
                url_requisicao,
                allow_redirects=True,
                stream=True,
                timeout=self.timeout_segundos,
                headers={"User-Agent": ("Mozilla/5.0 " "(Windows NT 10.0; Win64; x64)")},
            )

        except requests.RequestException:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=self._criar_id_externo(mensagem),
                status=self.STATUS_ERRO,
                marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                url_original=url_original,
                motivo=motivo_falha,
            )

        try:
            url_final = str(
                getattr(
                    resposta,
                    "url",
                    "",
                )
                or ""
            ).strip()

            status = getattr(
                resposta,
                "status_code",
                None,
            )

            http_status = (
                status
                if isinstance(
                    status,
                    int,
                )
                else None
            )

            if not self._eh_dominio_oficial_ml(self._host(url_final)):
                return ResultadoResolucaoSocialScout(
                    fonte=mensagem.fonte,
                    id_externo=self._criar_id_externo(mensagem),
                    status=self.STATUS_NAO_SUPORTADO,
                    marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                    url_original=url_original,
                    url_destino=url_final,
                    http_status=http_status,
                    motivo=("link_curto_nao_levou_ao_" "mercado_livre_oficial"),
                )

            if self._eh_pagina_social(url_final):
                try:
                    conteudo = resposta.text or ""

                except requests.RequestException:
                    return ResultadoResolucaoSocialScout(
                        fonte=mensagem.fonte,
                        id_externo=(self._criar_id_externo(mensagem)),
                        status=self.STATUS_ERRO,
                        marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                        url_original=url_original,
                        url_destino=url_final,
                        http_status=http_status,
                        motivo=("falha_ao_ler_pagina_social"),
                    )

                return self._classificar_pagina_social(
                    mensagem=mensagem,
                    deteccao=deteccao,
                    url_original=url_original,
                    url_social=url_final,
                    conteudo=conteudo,
                    http_status=http_status,
                )

            return self._classificar_mercado_livre(
                mensagem=mensagem,
                url_original=url_original,
                url_destino=url_final,
                http_status=http_status,
            )

        finally:
            resposta.close()

    def _classificar_pagina_social(
        self,
        *,
        mensagem: MensagemSocialScout,
        deteccao: ResultadoDeteccaoSocialScout,
        url_original: str,
        url_social: str,
        conteudo: str,
        http_status: int | None,
    ) -> ResultadoResolucaoSocialScout:
        titulo_destino = self._extrair_meta(
            conteudo=conteudo,
            propriedade="og:title",
        )

        if not titulo_destino:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=self._criar_id_externo(mensagem),
                status=self.STATUS_NAO_SUPORTADO,
                marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                url_original=url_original,
                url_destino=(self._limpar_tracking(url_social)),
                http_status=http_status,
                motivo=("pagina_social_sem_titulo_destacado"),
            )

        if not self._titulos_compativeis(
            deteccao.titulo,
            titulo_destino,
        ):
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=self._criar_id_externo(mensagem),
                status=self.STATUS_NAO_SUPORTADO,
                marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                url_original=url_original,
                url_destino=(self._limpar_tracking(url_social)),
                http_status=http_status,
                motivo=("pagina_social_titulo_divergente"),
            )

        candidatos = self._extrair_cards_destacados(conteudo)

        if not candidatos:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=self._criar_id_externo(mensagem),
                status=self.STATUS_NAO_SUPORTADO,
                marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                url_original=url_original,
                url_destino=(self._limpar_tracking(url_social)),
                http_status=http_status,
                motivo=("pagina_social_sem_card_destacado"),
            )

        produtos: dict[
            tuple[str | None, str | None],
            str,
        ] = {}

        for candidato in candidatos:
            url_limpa = self._limpar_url_identidade_mercado_livre(candidato)

            identificacao = self.identificador_mercado_livre.identificar(url_limpa)

            if not identificacao.id_produto and not identificacao.id_anuncio:
                continue

            chave = (
                identificacao.id_produto,
                identificacao.id_anuncio,
            )

            produtos.setdefault(
                chave,
                url_limpa,
            )

        if not produtos:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=self._criar_id_externo(mensagem),
                status=self.STATUS_NAO_SUPORTADO,
                marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                url_original=url_original,
                url_destino=(self._limpar_tracking(url_social)),
                http_status=http_status,
                motivo=("card_destacado_sem_identificador"),
            )

        if len(produtos) != 1:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=self._criar_id_externo(mensagem),
                status=self.STATUS_NAO_SUPORTADO,
                marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                url_original=url_original,
                url_destino=(self._limpar_tracking(url_social)),
                http_status=http_status,
                motivo=("pagina_social_card_destacado_ambiguo"),
            )

        (
            id_produto,
            id_anuncio,
        ), url_produto = next(iter(produtos.items()))

        return ResultadoResolucaoSocialScout(
            fonte=mensagem.fonte,
            id_externo=self._criar_id_externo(mensagem),
            status=self.STATUS_RESOLVIDO,
            marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
            tipo_destino="produto",
            url_original=url_original,
            url_destino=url_produto,
            id_produto=id_produto,
            id_anuncio=id_anuncio,
            http_status=http_status,
            motivo=("produto_social_mercado_livre_identificado"),
        )

    def _classificar_mercado_livre(
        self,
        *,
        mensagem: MensagemSocialScout,
        url_original: str,
        url_destino: str,
        http_status: int | None,
    ) -> ResultadoResolucaoSocialScout:
        url_limpa = self._limpar_url_identidade_mercado_livre(url_destino)

        identificacao = self.identificador_mercado_livre.identificar(url_limpa)

        if not self._eh_dominio_oficial_ml(identificacao.dominio):
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=self._criar_id_externo(mensagem),
                status=self.STATUS_NAO_SUPORTADO,
                marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                url_original=url_original,
                url_destino=url_limpa,
                http_status=http_status,
                motivo=("destino_nao_e_mercado_livre_oficial"),
            )

        id_produto = identificacao.id_produto
        id_anuncio = identificacao.id_anuncio

        if not id_produto and not id_anuncio:
            return ResultadoResolucaoSocialScout(
                fonte=mensagem.fonte,
                id_externo=self._criar_id_externo(mensagem),
                status=self.STATUS_NAO_SUPORTADO,
                marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
                tipo_destino="produto_nao_identificado",
                url_original=url_original,
                url_destino=url_limpa,
                http_status=http_status,
                motivo=("mercado_livre_sem_identificador"),
            )

        return ResultadoResolucaoSocialScout(
            fonte=mensagem.fonte,
            id_externo=self._criar_id_externo(mensagem),
            status=self.STATUS_RESOLVIDO,
            marketplace=(self.MARKETPLACE_MERCADO_LIVRE),
            tipo_destino="produto",
            url_original=url_original,
            url_destino=url_limpa,
            id_produto=id_produto,
            id_anuncio=id_anuncio,
            http_status=http_status,
            motivo="produto_mercado_livre_identificado",
        )

    def _extrair_cards_destacados(
        self,
        conteudo: str,
    ) -> tuple[str, ...]:
        normalizado = html_lib.unescape(str(conteudo or ""))

        normalizado = re.sub(
            r"\\u002[fF]",
            "/",
            normalizado,
        )

        normalizado = re.sub(
            r"\\u003[aA]",
            ":",
            normalizado,
        )

        normalizado = re.sub(
            r"\\u0026",
            "&",
            normalizado,
            flags=re.IGNORECASE,
        )

        normalizado = re.sub(
            r"\\u003[dD]",
            "=",
            normalizado,
        )

        normalizado = normalizado.replace(
            r"\/",
            "/",
        )

        encontrados: list[str] = []

        for correspondencia in self.PADRAO_URL_MERCADO_LIVRE.finditer(normalizado):
            url = correspondencia.group().strip()

            url_casefold = url.casefold()

            eh_card_destacado = "c_id=/home/card-featured/element" in url_casefold or (
                "c_id=%2fhome%2fcard-featured" "%2felement" in url_casefold
            )

            if not eh_card_destacado:
                continue

            if url not in encontrados:
                encontrados.append(url)

        return tuple(encontrados)

    def _extrair_meta(
        self,
        *,
        conteudo: str,
        propriedade: str,
    ) -> str | None:
        alvo = str(propriedade).strip().casefold()

        for tag in self.PADRAO_META.findall(conteudo or ""):
            atributos = {}

            for correspondencia in self.PADRAO_ATRIBUTO_HTML.finditer(tag):
                nome = correspondencia.group(1).strip().casefold()

                valor = html_lib.unescape(correspondencia.group(3)).strip()

                atributos[nome] = valor

            propriedade_tag = (atributos.get("property") or atributos.get("name") or "").casefold()

            if propriedade_tag != alvo:
                continue

            conteudo_meta = (atributos.get("content") or "").strip()

            if conteudo_meta:
                return conteudo_meta

        return None

    def _titulos_compativeis(
        self,
        titulo_origem: str,
        titulo_destino: str,
    ) -> bool:
        origem = self._tokens_titulo(titulo_origem)

        destino = set(self._tokens_titulo(titulo_destino))

        if not origem or not destino:
            return False

        correspondentes = [token for token in origem if token in destino]

        if len(origem) == 1:
            return bool(correspondentes)

        minimo = max(
            2,
            math.ceil(len(origem) * 0.6),
        )

        return len(correspondentes) >= minimo

    def _tokens_titulo(
        self,
        titulo: str,
    ) -> tuple[str, ...]:
        normalizado = self._normalizar_texto(titulo)

        resultado = []

        for token in re.findall(
            r"[a-z0-9]+",
            normalizado,
        ):
            if len(token) < 4:
                continue

            if token in self.TERMOS_GENERICOS_TITULO:
                continue

            if token not in resultado:
                resultado.append(token)

        return tuple(resultado)

    @staticmethod
    def _normalizar_texto(
        texto: str,
    ) -> str:
        valor = unicodedata.normalize(
            "NFKD",
            str(texto or ""),
        )

        valor = "".join(caractere for caractere in valor if not unicodedata.combining(caractere))

        return valor.casefold()

    def _limpar_url_identidade_mercado_livre(
        self,
        url: str,
    ) -> str:
        parsed = urlparse(str(url).strip())

        pares = parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )

        identidade: list[tuple[str, str]] = []

        prioridades = (
            "pdp_filters",
            "wid",
            "item_id",
        )

        for nome_alvo in prioridades:
            for (
                nome,
                valor,
            ) in pares:
                if nome.casefold() != nome_alvo:
                    continue

                if not self.PADRAO_MLB.search(valor):
                    continue

                identidade.append(
                    (
                        nome,
                        valor,
                    )
                )

                break

            if identidade:
                break

        query = urlencode(
            identidade,
            doseq=True,
        )

        return parsed._replace(
            params="",
            query=query,
            fragment="",
        ).geturl()

    def _eh_dominio_oficial_ml(
        self,
        host: str,
    ) -> bool:
        return host in self.identificador_mercado_livre.DOMINIOS

    def _eh_link_curto_ml(
        self,
        host: str,
    ) -> bool:
        return host in self.identificador_mercado_livre.DOMINIOS_AFILIADOS

    @staticmethod
    def _eh_pagina_social(
        url: str,
    ) -> bool:
        try:
            caminho = urlparse(str(url).strip()).path or ""

        except ValueError:
            return False

        return caminho.casefold().startswith("/social/")

    @staticmethod
    def _host(
        url: str,
    ) -> str:
        try:
            return (urlparse(str(url).strip()).hostname or "").strip().casefold()

        except ValueError:
            return ""

    @staticmethod
    def _limpar_tracking(
        url: str,
    ) -> str:
        parsed = urlparse(str(url).strip())

        return parsed._replace(
            params="",
            query="",
            fragment="",
        ).geturl()

    @staticmethod
    def _criar_id_externo(
        mensagem: MensagemSocialScout,
    ) -> str:
        return f"{mensagem.chat_id}:" f"{mensagem.message_id}"
