from __future__ import annotations

import hashlib
import re
import statistics
import unicodedata
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from config.historico_precos import (
    MINIMO_OBSERVACOES_PARA_ANALISE,
    MINIMO_OBSERVACOES_PARA_CONFIANCA_ALTA,
    MINIMO_OBSERVACOES_PARA_CONFIANCA_MEDIA,
    PENALIDADE_10_ACIMA_MEDIANA,
    PENALIDADE_20_ACIMA_MEDIANA,
    PESO_HISTORICO_CONFIANCA_ALTA,
    PESO_HISTORICO_CONFIANCA_BAIXA,
    PESO_HISTORICO_CONFIANCA_MEDIA,
    PONTOS_5_ABAIXO_MEDIANA,
    PONTOS_10_ABAIXO_MEDIANA,
    PONTOS_15_ABAIXO_MEDIANA,
    PONTOS_20_ABAIXO_MEDIANA,
    PONTOS_NOVO_MENOR_PRECO,
    PONTOS_PRECO_PROXIMO_MEDIANA,
)


class AnalisadorHistoricoPrecos:
    def criar_chave_produto(
        self,
        produto: dict[str, Any],
    ) -> str:
        link = self._obter_texto(
            produto,
            "link",
            "url",
            "produto_url",
        )

        id_mercado_livre = self._extrair_id_ml(link)

        if id_mercado_livre:
            return f"ml:{id_mercado_livre}"

        link_normalizado = self._normalizar_link(link)

        if link_normalizado:
            resumo = hashlib.sha256(link_normalizado.encode("utf-8")).hexdigest()[:24]

            return f"url:{resumo}"

        titulo = self._obter_texto(
            produto,
            "titulo",
            "nome",
            "title",
        )

        categoria = self._obter_texto(
            produto,
            "categoria",
            "category",
        )

        titulo_normalizado = self._normalizar_titulo_para_chave(titulo)

        origem = f"{titulo_normalizado}|" f"{self._normalizar_texto(categoria)}"

        resumo = hashlib.sha256(origem.encode("utf-8")).hexdigest()[:24]

        return f"titulo:{resumo}"

    def analisar(
        self,
        preco_atual: float | None,
        registros_anteriores: list[dict[str, Any]],
    ) -> dict[str, Any]:
        precos_anteriores = self._extrair_precos_validos(registros_anteriores)

        quantidade = len(precos_anteriores)

        resultado_padrao: dict[str, Any] = {
            "quantidade_observacoes_anteriores": quantidade,
            "preco_minimo_historico": None,
            "preco_maximo_historico": None,
            "preco_medio_historico": None,
            "preco_mediano_historico": None,
            "diferenca_mediana_percentual": None,
            "economia_mediana_reais": None,
            "nota_historico_bruta": 0,
            "peso_confianca_historico": 0.0,
            "nota_historico": 0,
            "classificacao_historico": ("histórico insuficiente"),
            "motivo_historico": ("Ainda não existem registros " "anteriores suficientes."),
        }

        if preco_atual is None or preco_atual <= 0:
            resultado_padrao["classificacao_historico"] = "preço atual inválido"

            resultado_padrao["motivo_historico"] = (
                "Não foi possível comparar porque " "o preço atual é inválido."
            )

            return resultado_padrao

        if quantidade < MINIMO_OBSERVACOES_PARA_ANALISE:
            return resultado_padrao

        minimo = min(precos_anteriores)

        maximo = max(precos_anteriores)

        media = statistics.fmean(precos_anteriores)

        mediana = statistics.median(precos_anteriores)

        diferenca_percentual = (preco_atual - mediana) / mediana * 100

        economia_reais = mediana - preco_atual

        nota_bruta, classificacao, motivo = self._calcular_nota_bruta(
            preco_atual=preco_atual,
            minimo=minimo,
            mediana=mediana,
            diferenca_percentual=diferenca_percentual,
        )

        peso_confianca = self._calcular_peso_confianca(quantidade)

        nota_final = round(nota_bruta * peso_confianca)

        return {
            "quantidade_observacoes_anteriores": quantidade,
            "preco_minimo_historico": round(
                minimo,
                2,
            ),
            "preco_maximo_historico": round(
                maximo,
                2,
            ),
            "preco_medio_historico": round(
                media,
                2,
            ),
            "preco_mediano_historico": round(
                mediana,
                2,
            ),
            "diferenca_mediana_percentual": round(
                diferenca_percentual,
                2,
            ),
            "economia_mediana_reais": round(
                economia_reais,
                2,
            ),
            "nota_historico_bruta": nota_bruta,
            "peso_confianca_historico": (peso_confianca),
            "nota_historico": nota_final,
            "classificacao_historico": classificacao,
            "motivo_historico": motivo,
        }

    @staticmethod
    def _calcular_nota_bruta(
        preco_atual: float,
        minimo: float,
        mediana: float,
        diferenca_percentual: float,
    ) -> tuple[int, str, str]:
        if preco_atual < minimo:
            return (
                PONTOS_NOVO_MENOR_PRECO,
                "novo menor preço",
                ("O preço atual está abaixo de todos " "os registros anteriores."),
            )

        if diferenca_percentual <= -20:
            return (
                PONTOS_20_ABAIXO_MEDIANA,
                "oferta excepcional",
                ("O preço atual está pelo menos 20% " "abaixo da mediana histórica."),
            )

        if diferenca_percentual <= -15:
            return (
                PONTOS_15_ABAIXO_MEDIANA,
                "oferta excelente",
                ("O preço atual está pelo menos 15% " "abaixo da mediana histórica."),
            )

        if diferenca_percentual <= -10:
            return (
                PONTOS_10_ABAIXO_MEDIANA,
                "oferta muito boa",
                ("O preço atual está pelo menos 10% " "abaixo da mediana histórica."),
            )

        if diferenca_percentual <= -5:
            return (
                PONTOS_5_ABAIXO_MEDIANA,
                "boa oferta",
                ("O preço atual está pelo menos 5% " "abaixo da mediana histórica."),
            )

        if diferenca_percentual <= 3:
            return (
                PONTOS_PRECO_PROXIMO_MEDIANA,
                "preço comum",
                ("O preço atual está próximo da " "mediana histórica."),
            )

        if diferenca_percentual >= 20:
            return (
                PENALIDADE_20_ACIMA_MEDIANA,
                "preço ruim",
                ("O preço atual está pelo menos 20% " "acima da mediana histórica."),
            )

        if diferenca_percentual >= 10:
            return (
                PENALIDADE_10_ACIMA_MEDIANA,
                "preço acima do normal",
                ("O preço atual está pelo menos 10% " "acima da mediana histórica."),
            )

        return (
            0,
            "sem vantagem histórica",
            ("O preço atual não apresenta vantagem " "relevante sobre o histórico."),
        )

    @staticmethod
    def _calcular_peso_confianca(
        quantidade_observacoes: int,
    ) -> float:
        if quantidade_observacoes >= MINIMO_OBSERVACOES_PARA_CONFIANCA_ALTA:
            return PESO_HISTORICO_CONFIANCA_ALTA

        if quantidade_observacoes >= MINIMO_OBSERVACOES_PARA_CONFIANCA_MEDIA:
            return PESO_HISTORICO_CONFIANCA_MEDIA

        return PESO_HISTORICO_CONFIANCA_BAIXA

    @staticmethod
    def _extrair_precos_validos(
        registros: list[dict[str, Any]],
    ) -> list[float]:
        precos: list[float] = []

        for registro in registros:
            valor = registro.get("preco")

            if isinstance(valor, bool):
                continue

            try:
                preco = float(valor)

            except (
                TypeError,
                ValueError,
            ):
                continue

            if preco > 0:
                precos.append(preco)

        return precos

    @staticmethod
    def _extrair_id_ml(
        link: str,
    ) -> str:
        if not link:
            return ""

        correspondencia = re.search(
            r"\bMLB[-_]?(\d{6,})\b",
            link,
            flags=re.IGNORECASE,
        )

        if not correspondencia:
            return ""

        return f"MLB{correspondencia.group(1)}"

    @staticmethod
    def _normalizar_link(
        link: str,
    ) -> str:
        if not link:
            return ""

        try:
            partes = urlsplit(link.strip())

        except ValueError:
            return ""

        if not partes.scheme or not partes.netloc:
            return ""

        caminho = partes.path.rstrip("/")

        return urlunsplit(
            (
                partes.scheme.lower(),
                partes.netloc.lower(),
                caminho,
                "",
                "",
            )
        )

    def _normalizar_titulo_para_chave(
        self,
        titulo: str,
    ) -> str:
        titulo = self._normalizar_texto(titulo)

        termos_ignorados = {
            "preto",
            "preta",
            "branco",
            "branca",
            "azul",
            "rosa",
            "rose",
            "roxo",
            "roxa",
            "verde",
            "vermelho",
            "vermelha",
            "cinza",
            "cor",
            "novo",
            "nova",
            "original",
            "lacrado",
            "lacrada",
        }

        tokens = re.findall(
            r"[a-z0-9]+",
            titulo,
        )

        tokens = [token for token in tokens if token not in termos_ignorados]

        return " ".join(tokens[:18])

    @staticmethod
    def _normalizar_texto(
        texto: str,
    ) -> str:
        texto = unicodedata.normalize(
            "NFKD",
            texto,
        )

        texto = texto.encode(
            "ascii",
            "ignore",
        ).decode("ascii")

        texto = texto.lower()

        texto = re.sub(
            r"\s+",
            " ",
            texto,
        )

        return texto.strip()

    @staticmethod
    def _obter_texto(
        produto: dict[str, Any],
        *chaves: str,
    ) -> str:
        for chave in chaves:
            valor = produto.get(chave)

            if valor is None:
                continue

            texto = str(valor).strip()

            if texto:
                return texto

        return ""
