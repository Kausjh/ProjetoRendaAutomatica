# 63.8738, -149.7525

from __future__ import annotations

import logging
import re
import time
import unicodedata
from dataclasses import dataclass

from models.oferta import Oferta
from scrapers.base_scraper import BaseScraper
from services.aliexpress_preco_cdp_service import (
    AliExpressPrecoCdpService,
)
from services.awin_product_feed_service import (
    AwinProductFeedService,
    ProdutoFeedAwin,
)
from services.classificador_produto import (
    ClassificadorProduto,
    ResultadoClassificacaoProduto,
)
from services.validador_preco_aliexpress import (
    ResultadoPrecoAliExpress,
)

logger = logging.getLogger(__name__)


@dataclass(
    frozen=True,
    slots=True,
)
class _CandidatoAliExpress:
    produto: ProdutoFeedAwin
    classificacao: ResultadoClassificacaoProduto

    @property
    def relevancia(self) -> float:
        return float(self.classificacao.relevancia)

    @property
    def desconto_feed(self) -> float:
        valor = self.produto.desconto_percentual_feed or 0.0

        return max(
            float(valor),
            0.0,
        )


class AliExpressScraper(BaseScraper):
    MARKETPLACE = "aliexpress"
    LOJA = "AliExpress"

    URL_PRODUTO = "https://pt.aliexpress.com/" "item/{produto_id}.html"

    # Feeds relevantes ao publico atual do Radar.
    FEEDS_PADRAO: tuple[str, ...] = (
        "47213",  # Communication & Equipment
        "47215",  # Computer_Office
        "47217",  # Consumer_Electronics
        "47219",  # Electrical_Equipment_Supplies
        "47221",  # Food
        "47227",  # Home_Appliances
        "47245",  # Mobile Phone Accessories & Parts
        "47247",  # Mobile Phones
        "47253",  # Office & School Supplies
    )

    def __init__(
        self,
        feed_service: AwinProductFeedService | None = None,
        preco_service: AliExpressPrecoCdpService | None = None,
        classificador: ClassificadorProduto | None = None,
        feed_ids: tuple[str, ...] | None = None,
        itens_por_feed: int = 30,
        candidatos_por_feed: int = 5,
        max_validacoes: int = 18,
        deslocamento_feed: int | None = None,
    ) -> None:
        if itens_por_feed <= 0:
            raise ValueError("itens_por_feed precisa ser maior que zero.")

        if candidatos_por_feed <= 0:
            raise ValueError("candidatos_por_feed precisa " "ser maior que zero.")

        if max_validacoes <= 0:
            raise ValueError("max_validacoes precisa ser maior que zero.")

        feeds = feed_ids if feed_ids is not None else self.FEEDS_PADRAO

        self.feed_ids = tuple(str(feed_id).strip() for feed_id in feeds if str(feed_id).strip())

        if not self.feed_ids:
            raise ValueError("Nenhum feed AliExpress foi configurado.")

        self.feed_service = feed_service if feed_service is not None else AwinProductFeedService()

        self.preco_service = (
            preco_service if preco_service is not None else AliExpressPrecoCdpService()
        )

        self.classificador = classificador if classificador is not None else ClassificadorProduto()

        self.itens_por_feed = int(itens_por_feed)

        self.candidatos_por_feed = int(candidatos_por_feed)

        self.max_validacoes = int(max_validacoes)

        if deslocamento_feed is not None and deslocamento_feed < 0:
            raise ValueError("deslocamento_feed nao pode ser negativo.")

        self.deslocamento_feed = deslocamento_feed

    def buscar_ofertas(
        self,
        limite: int = 5,
    ) -> list[Oferta]:
        if limite <= 0:
            logger.warning("O limite do AliExpress deve " "ser maior que zero.")
            return []

        candidatos = self._buscar_candidatos()

        if not candidatos:
            logger.info("AliExpress nao encontrou " "candidatos do nicho.")
            return []

        quantidade_validar = min(
            len(candidatos),
            self.max_validacoes,
            max(
                limite * 2,
                8,
            ),
        )

        candidatos = candidatos[:quantidade_validar]

        ids = [candidato.produto.merchant_product_id for candidato in candidatos]

        logger.info(
            "AliExpress: %s candidato(s) "
            "pre-classificado(s); "
            "%s seguirao para validacao BRL.",
            len(candidatos),
            len(ids),
        )

        resultados = self.preco_service.validar_produtos(ids)

        ofertas: list[Oferta] = []

        for candidato in candidatos:
            produto = candidato.produto

            resultado = resultados.get(produto.merchant_product_id)

            if resultado is None or not resultado.valido or resultado.preco is None:
                if resultado is not None:
                    logger.debug(
                        "AliExpress rejeitado na " "validacao de preco: %s | %s",
                        produto.merchant_product_id,
                        resultado.motivo,
                    )

                continue

            if not self._sku_coerente_com_titulo(
                titulo=produto.nome,
                sku_atributo=(resultado.sku_atributo_selecionado),
            ):
                logger.debug(
                    "AliExpress rejeitado por SKU "
                    "incoerente com titulo: "
                    "%s | titulo=%s | sku=%s",
                    produto.merchant_product_id,
                    produto.nome,
                    (resultado.sku_atributo_selecionado),
                )
                continue

            oferta = self._criar_oferta(
                candidato=candidato,
                resultado=resultado,
            )

            ofertas.append(oferta)

            if len(ofertas) >= limite:
                break

        logger.info(
            "AliExpress retornou %s oferta(s) " "com preco BRL validado.",
            len(ofertas),
        )

        return ofertas

    def _buscar_candidatos(
        self,
    ) -> list[_CandidatoAliExpress]:
        candidatos: list[_CandidatoAliExpress] = []

        deslocamento = self._obter_deslocamento_feed()

        limite_leitura = deslocamento + self.itens_por_feed

        for feed_id in self.feed_ids:
            candidatos_feed: list[_CandidatoAliExpress] = []

            try:
                produtos = self.feed_service.iterar_produtos(
                    feed_id=feed_id,
                    limite=limite_leitura,
                )

                for indice, produto in enumerate(produtos):
                    if indice < deslocamento:
                        continue

                    candidato = self._pre_classificar(produto)

                    if candidato is None:
                        continue

                    candidatos_feed.append(candidato)

            except Exception:
                logger.exception(
                    "Falha ao processar feed " "AliExpress %s.",
                    feed_id,
                )
                continue

            candidatos_feed.sort(
                key=self._chave_ranking,
                reverse=True,
            )

            candidatos.extend(candidatos_feed[: self.candidatos_por_feed])

        # Um mesmo produto pode aparecer em
        # mais de um feed.
        por_produto: dict[
            str,
            _CandidatoAliExpress,
        ] = {}

        for candidato in candidatos:
            produto_id = candidato.produto.merchant_product_id

            atual = por_produto.get(produto_id)

            if atual is None or self._chave_ranking(candidato) > self._chave_ranking(atual):
                por_produto[produto_id] = candidato

        resultado = list(por_produto.values())

        resultado.sort(
            key=self._chave_ranking,
            reverse=True,
        )

        resultado = self._remover_quase_duplicados(resultado)

        return self._priorizar_diversidade(resultado)

    def _pre_classificar(
        self,
        produto: ProdutoFeedAwin,
    ) -> _CandidatoAliExpress | None:
        produto_id = str(produto.merchant_product_id).strip()

        nome = str(produto.nome).strip()

        if not produto_id or not produto_id.isdigit() or not nome:
            return None

        # Oferta efemera usada apenas porque o
        # classificador global atual recebe Oferta.
        # Ela nunca segue para historico/pipeline.
        preco_origem = (
            produto.preco_feed
            if (produto.preco_feed is not None and produto.preco_feed > 0)
            else 1.0
        )

        oferta_temporaria = Oferta(
            nome=nome,
            loja=self.LOJA,
            preco=float(preco_origem),
            preco_antigo=None,
            link=self.URL_PRODUTO.format(produto_id=produto_id),
            imagem=produto.imagem,
            moeda=(produto.moeda or ""),
            marketplace=self.MARKETPLACE,
            id_produto=produto_id,
        )

        classificacao = self.classificador.classificar(oferta_temporaria)

        if not classificacao.eh_nicho:
            return None

        if not self._candidato_coerente(
            produto=produto,
            classificacao=classificacao,
        ):
            return None

        return _CandidatoAliExpress(
            produto=produto,
            classificacao=classificacao,
        )

    @classmethod
    def _candidato_coerente(
        cls,
        produto: ProdutoFeedAwin,
        classificacao: ResultadoClassificacaoProduto,
    ) -> bool:
        texto = cls._normalizar_titulo(produto.nome)

        ruidos = (
            "cleaning kit",
            "cleaner kit",
            "cleaning pen",
            "cleaning brush",
            "dust plug",
            "eject pin",
            "sim card tray removal",
            "screen opener",
            "phone screen opener",
            "pry removal tool",
            "repair cards",
            "charging port cleaning",
            "screen auto clicker",
            "screen tapper",
            "junction box",
            "distribution box",
            "module housing",
            "plastic enclosure",
        )

        if any(ruido in texto for ruido in ruidos):
            return False

        feed_id = str(produto.feed_id).strip()

        categoria = classificacao.categoria or ""

        # O feed 47245 e de acessorios/pecas
        # para celulares. Referencias a iPhone,
        # iPad etc. nao transformam um acessorio
        # no aparelho principal.
        if feed_id == "47245" and categoria in {
            "Celular",
            "Tablet e e-reader",
        }:
            return False

        return True

    @classmethod
    def _remover_quase_duplicados(
        cls,
        candidatos: list[_CandidatoAliExpress],
    ) -> list[_CandidatoAliExpress]:
        resultado: list[_CandidatoAliExpress] = []

        for candidato in candidatos:
            duplicado = False

            for existente in resultado:
                if candidato.classificacao.categoria != existente.classificacao.categoria:
                    continue

                similaridade = cls._similaridade_titulos(
                    candidato.produto.nome,
                    existente.produto.nome,
                )

                if similaridade >= 0.72:
                    duplicado = True
                    break

            if not duplicado:
                resultado.append(candidato)

        return resultado

    @classmethod
    def _priorizar_diversidade(
        cls,
        candidatos: list[_CandidatoAliExpress],
    ) -> list[_CandidatoAliExpress]:
        # Na primeira passagem permitimos no
        # maximo dois candidatos por categoria.
        # O excedente continua disponivel depois,
        # portanto nao perdemos produtos.
        principais: list[_CandidatoAliExpress] = []

        excedentes: list[_CandidatoAliExpress] = []

        contagem: dict[
            str,
            int,
        ] = {}

        for candidato in candidatos:
            categoria = candidato.classificacao.categoria or "sem_categoria"

            quantidade = contagem.get(
                categoria,
                0,
            )

            if quantidade < 2:
                principais.append(candidato)

                contagem[categoria] = quantidade + 1

            else:
                excedentes.append(candidato)

        return principais + excedentes

    @classmethod
    def _similaridade_titulos(
        cls,
        titulo_a: str,
        titulo_b: str,
    ) -> float:
        tokens_a = cls._tokens_titulo(titulo_a)

        tokens_b = cls._tokens_titulo(titulo_b)

        if not tokens_a or not tokens_b:
            return 0.0

        uniao = tokens_a | tokens_b

        if not uniao:
            return 0.0

        intersecao = tokens_a & tokens_b

        return len(intersecao) / len(uniao)

    @classmethod
    def _tokens_titulo(
        cls,
        titulo: str,
    ) -> set[str]:
        ignorar = {
            "a",
            "an",
            "and",
            "com",
            "da",
            "de",
            "do",
            "for",
            "new",
            "of",
            "para",
            "the",
            "to",
            "with",
            "2026",
        }

        return {
            token
            for token in cls._normalizar_titulo(titulo).split()
            if (token not in ignorar and len(token) >= 2)
        }

    @staticmethod
    def _normalizar_titulo(
        titulo: str,
    ) -> str:
        texto = "".join(
            caractere
            for caractere in unicodedata.normalize(
                "NFKD",
                str(titulo),
            )
            if not unicodedata.combining(caractere)
        )

        texto = texto.casefold()

        texto = re.sub(
            r"[^a-z0-9]+",
            " ",
            texto,
        )

        return re.sub(
            r"\s+",
            " ",
            texto,
        ).strip()

    @classmethod
    def _sku_coerente_com_titulo(
        cls,
        titulo: str,
        sku_atributo: str | None,
    ) -> bool:
        if not sku_atributo:
            return True

        capacidades_sku = cls._extrair_capacidades_gb(sku_atributo)

        if not capacidades_sku:
            return True

        capacidades_titulo = cls._extrair_capacidades_armazenamento_gb(titulo)

        if not capacidades_titulo:
            return True

        return bool(capacidades_sku & capacidades_titulo)

    @classmethod
    def _extrair_capacidades_armazenamento_gb(
        cls,
        texto: str,
    ) -> set[int]:
        texto = cls._normalizar_capacidades(texto)

        resultado: set[int] = set()

        armazenamento = r"(?:ssd|nvme|hdd|rom|emmc|storage)"

        # Ex.: 1TB/2TB SSD
        padrao_duplo = re.compile(
            r"(\d+(?:\.\d+)?)\s*(gb|tb)"
            r"\s*(?:/|,|-|or|ou)\s*"
            r"(\d+(?:\.\d+)?)\s*(gb|tb)"
            r"\s*" + armazenamento
        )

        for achado in padrao_duplo.finditer(texto):
            resultado.add(
                cls._capacidade_para_gb(
                    achado.group(1),
                    achado.group(2),
                )
            )

            resultado.add(
                cls._capacidade_para_gb(
                    achado.group(3),
                    achado.group(4),
                )
            )

        # Ex.: 1/2TB SSD
        padrao_unidade_compartilhada = re.compile(
            r"(\d+(?:\.\d+)?)\s*/\s*" r"(\d+(?:\.\d+)?)\s*(gb|tb)" r"\s*" + armazenamento
        )

        for achado in padrao_unidade_compartilhada.finditer(texto):
            unidade = achado.group(3)

            resultado.add(
                cls._capacidade_para_gb(
                    achado.group(1),
                    unidade,
                )
            )

            resultado.add(
                cls._capacidade_para_gb(
                    achado.group(2),
                    unidade,
                )
            )

        # Ex.: 2TB SSD / 512GB NVMe
        padrao_normal = re.compile(r"(\d+(?:\.\d+)?)\s*(gb|tb)" r"\s*" + armazenamento)

        for achado in padrao_normal.finditer(texto):
            resultado.add(
                cls._capacidade_para_gb(
                    achado.group(1),
                    achado.group(2),
                )
            )

        # Ex.: SSD 2TB / NVMe 512GB
        padrao_invertido = re.compile(
            armazenamento + r"\s*(?:m\.?2\s*)?" r"(\d+(?:\.\d+)?)\s*(gb|tb)"
        )

        for achado in padrao_invertido.finditer(texto):
            resultado.add(
                cls._capacidade_para_gb(
                    achado.group(1),
                    achado.group(2),
                )
            )

        return resultado

    @classmethod
    def _extrair_capacidades_gb(
        cls,
        texto: str,
    ) -> set[int]:
        texto = cls._normalizar_capacidades(texto)

        resultado: set[int] = set()

        for achado in re.finditer(
            r"(?<!\d)" r"(\d+(?:\.\d+)?)\s*(gb|tb)\b",
            texto,
        ):
            resultado.add(
                cls._capacidade_para_gb(
                    achado.group(1),
                    achado.group(2),
                )
            )

        return resultado

    @staticmethod
    def _capacidade_para_gb(
        valor: str,
        unidade: str,
    ) -> int:
        numero = float(valor)

        if unidade.casefold() == "tb":
            numero *= 1024

        return int(round(numero))

    @staticmethod
    def _normalizar_capacidades(
        texto: str,
    ) -> str:
        texto = "".join(
            caractere
            for caractere in unicodedata.normalize(
                "NFKD",
                str(texto),
            )
            if not unicodedata.combining(caractere)
        )

        texto = texto.casefold().replace(",", ".")

        return re.sub(
            r"\s+",
            " ",
            texto,
        ).strip()

    def _criar_oferta(
        self,
        candidato: _CandidatoAliExpress,
        resultado: ResultadoPrecoAliExpress,
    ) -> Oferta:
        produto = candidato.produto

        produto_id = produto.merchant_product_id

        preco = float(resultado.preco)

        preco_antigo = None

        if (
            not resultado.promocao_novo_usuario
            and resultado.preco_normal is not None
            and resultado.preco_normal > preco
        ):
            preco_antigo = float(resultado.preco_normal)

        preco_novo_usuario = None
        moeda_novo_usuario = None

        if resultado.promocao_novo_usuario and resultado.preco_novo_usuario is not None:
            preco_novo_usuario = float(resultado.preco_novo_usuario)

            moeda_novo_usuario = "R$"

        oferta = Oferta(
            nome=produto.nome,
            loja=self.LOJA,
            preco=preco,
            preco_antigo=preco_antigo,
            link=self.URL_PRODUTO.format(produto_id=produto_id),
            imagem=produto.imagem,
            moeda="R$",
            preco_novo_usuario=(preco_novo_usuario),
            moeda_novo_usuario=(moeda_novo_usuario),
            preco_origem=(produto.preco_feed),
            moeda_origem=(produto.moeda or None),
            marketplace=self.MARKETPLACE,
            id_produto=produto_id,
        )

        if oferta.desconto_percentual > 0:
            oferta.desconto_anunciado = oferta.desconto_percentual

        return oferta

    @staticmethod
    def _chave_ranking(
        candidato: _CandidatoAliExpress,
    ) -> tuple[
        float,
        float,
        str,
    ]:
        desconto = min(
            candidato.desconto_feed,
            80.0,
        )

        return (
            candidato.relevancia,
            desconto,
            candidato.produto.nome,
        )

    def _obter_deslocamento_feed(
        self,
    ) -> int:
        if self.deslocamento_feed is not None:
            return self.deslocamento_feed

        # Troca a faixa a cada 30 minutos.
        # Seis faixas percorrem ate 180 itens
        # de cada feed sem manter estado local.
        janela_meia_hora = int(time.time() // 1800)

        indice = janela_meia_hora % 6

        return indice * self.itens_por_feed
