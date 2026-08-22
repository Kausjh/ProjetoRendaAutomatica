# 63.8738, -149.7525

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True, slots=True)
class ResultadoFamiliaProduto:
    nome_familia: str
    chave_familia: str
    confianca: float
    tokens_base: tuple[str, ...]


class IdentificadorFamiliaProduto:
    """Agrupa variantes editoriais do mesmo produto.

    A família remove diferenças cosméticas/mercadológicas, mas preserva
    diferenças materiais como capacidade, tamanho, geração, versão Ti/XT,
    quantidade de memória e outros números relevantes.

    Exemplo:
    Cloud II preto e Cloud II vermelho -> mesma família.
    SSD 1 TB e SSD 2 TB -> famílias diferentes.
    """

    CORES = frozenset(
        {
            "preto",
            "preta",
            "black",
            "vermelho",
            "vermelha",
            "red",
            "branco",
            "branca",
            "white",
            "azul",
            "blue",
            "verde",
            "green",
            "rosa",
            "pink",
            "roxo",
            "purple",
            "cinza",
            "gray",
            "grey",
            "prata",
            "silver",
            "dourado",
            "gold",
            "laranja",
            "orange",
        }
    )

    RUIDO = frozenset(
        {
            "gamer",
            "gaming",
            "novo",
            "nova",
            "original",
            "oficial",
            "produto",
            "cor",
            "c",
            "com",
            "de",
            "da",
            "do",
            "das",
            "dos",
            "para",
            "por",
            "e",
            "em",
            "the",
            "edition",
            "edicao",
            "envio",
            "imediato",
            "pronta",
            "entrega",
            "frete",
            "gratis",
            "mercado",
            "livre",
        }
    )

    # Palavras que carregam diferenças materiais e portanto NUNCA são
    # removidas da família.
    SUFIXOS_MATERIAIS = frozenset(
        {
            "ti",
            "super",
            "xt",
            "xtx",
            "pro",
            "max",
            "plus",
            "ultra",
            "slim",
            "digital",
            "oled",
            "qled",
            "mini",
            "wireless",
        }
    )

    def identificar(self, oferta: Oferta) -> ResultadoFamiliaProduto:
        texto = self._normalizar(oferta.nome)
        categoria = self._normalizar(oferta.categoria or "produto")
        marca = self._normalizar(oferta.marca or "")

        tokens = self._tokens_significativos(texto)

        # Se já existe modelo canônico confiável, ele é a âncora mais forte.
        if (
            oferta.modelo_produto
            and oferta.confianca_normalizacao >= 90
            and oferta.categoria not in {"Computador e Mini PC", "Notebook", "Kit upgrade"}
        ):
            modelo = self._normalizar(oferta.modelo_produto)
            base = self._tokens_significativos(modelo)

            # Marca separada evita colisões quando modelos genéricos coincidem.
            partes = [categoria]
            if marca:
                partes.append(marca)
            partes.extend(base)

            chave = self._slug(" ".join(dict.fromkeys(partes)))
            nome = " ".join(dict.fromkeys(partes))

            resultado = ResultadoFamiliaProduto(
                nome_familia=nome,
                chave_familia=chave,
                confianca=96.0,
                tokens_base=tuple(base),
            )
            self._aplicar(oferta, resultado)
            return resultado

        # Para títulos comuns, usamos os tokens significativos do próprio
        # anúncio. Cor e ruído comercial saem; números/capacidades permanecem.
        partes = [categoria]
        if marca:
            partes.append(marca)

        partes.extend(tokens)
        partes = list(dict.fromkeys(partes))

        # Família muito curta é perigosa para deduplicação.
        confianca = 88.0 if len(tokens) >= 3 else 65.0

        nome = " ".join(partes)
        chave = self._slug(nome)

        resultado = ResultadoFamiliaProduto(
            nome_familia=nome,
            chave_familia=chave,
            confianca=confianca,
            tokens_base=tuple(tokens),
        )
        self._aplicar(oferta, resultado)
        return resultado

    def mesma_familia(
        self,
        oferta_a: Oferta,
        oferta_b: Oferta,
    ) -> bool:
        a = self.identificar(oferta_a)
        b = self.identificar(oferta_b)

        if a.chave_familia == b.chave_familia:
            return True

        if oferta_a.categoria != oferta_b.categoria:
            return False

        if (
            oferta_a.marca
            and oferta_b.marca
            and self._normalizar(oferta_a.marca) != self._normalizar(oferta_b.marca)
        ):
            return False

        tokens_a = set(a.tokens_base)
        tokens_b = set(b.tokens_base)

        if not tokens_a or not tokens_b:
            return False

        # Números diferentes quase sempre significam variante material.
        numeros_a = self._tokens_numericos(tokens_a)
        numeros_b = self._tokens_numericos(tokens_b)

        if numeros_a != numeros_b:
            return False

        intersecao = len(tokens_a & tokens_b)
        uniao = len(tokens_a | tokens_b)
        similaridade = intersecao / uniao if uniao else 0.0

        return similaridade >= 0.72

    def _tokens_significativos(self, texto: str) -> list[str]:
        tokens: list[str] = []

        for token in texto.split():
            if token in self.CORES or token in self.RUIDO:
                continue

            if len(token) <= 1 and not token.isdigit():
                continue

            tokens.append(token)

        return tokens

    @staticmethod
    def _tokens_numericos(tokens: set[str]) -> set[str]:
        return {token for token in tokens if any(caractere.isdigit() for caractere in token)}

    @staticmethod
    def _aplicar(
        oferta: Oferta,
        resultado: ResultadoFamiliaProduto,
    ) -> None:
        oferta.familia_produto = resultado.nome_familia
        oferta.chave_familia_produto = resultado.chave_familia
        oferta.confianca_familia = resultado.confianca

    @staticmethod
    def _slug(texto: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", texto).strip("_")

    @staticmethod
    def _normalizar(texto: str) -> str:
        sem_acentos = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(caractere)
        )
        sem_acentos = sem_acentos.casefold()
        sem_acentos = re.sub(r"[^a-z0-9.+/\- ]", " ", sem_acentos)
        return re.sub(r"\s+", " ", sem_acentos).strip()
