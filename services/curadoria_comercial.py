import re
import unicodedata
from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True)
class ResultadoCuradoriaComercial:
    nota: float
    marca: str | None
    pontos_categoria: float
    pontos_marca: float
    pontos_ticket: float
    motivos: list[str]


class CuradoriaComercial:
    """
    Calcula o potencial comercial de uma oferta.

    A nota máxima é 20 pontos:

    - Categoria: até 10 pontos
    - Marca: até 5 pontos
    - Faixa de preço: até 5 pontos
    """

    NOTA_MAXIMA = 20.0

    PONTOS_CATEGORIAS: dict[str, float] = {
        "Placa de vídeo": 10.0,
        "Processador": 10.0,
        "Notebook gamer": 9.5,
        "Computador gamer": 9.0,
        "Monitor": 9.0,
        "Armazenamento": 8.5,
        "Memória RAM": 8.5,
        "Placa-mãe": 8.5,
        "Console": 8.0,
        "Fonte": 7.5,
        "Refrigeração": 7.0,
        "Teclado": 6.5,
        "Mouse": 6.5,
        "Headset e áudio": 6.5,
        "Controle": 6.5,
        "Streaming e captura": 6.0,
        "Simulação": 6.0,
        "Rede": 5.5,
        "Gabinete": 5.5,
        "Mobiliário gamer": 4.0,
    }

    PONTOS_MARCAS: dict[str, float] = {
        "amd": 5.0,
        "intel": 5.0,
        "nvidia": 5.0,
        "kingston": 5.0,
        "samsung": 5.0,
        "logitech": 5.0,
        "corsair": 5.0,
        "asus": 5.0,
        "msi": 5.0,
        "gigabyte": 5.0,
        "western digital": 5.0,
        "wd": 4.0,
        "crucial": 5.0,
        "sandisk": 4.5,
        "seagate": 4.5,
        "hyperx": 4.5,
        "razer": 4.5,
        "steelseries": 4.5,
        "aoc": 4.5,
        "lg": 4.5,
        "acer": 4.0,
        "dell": 4.0,
        "lenovo": 4.0,
        "redragon": 3.5,
        "cooler master": 4.0,
        "deepcool": 4.0,
        "pcyes": 3.0,
        "tp-link": 3.5,
        "8bitdo": 4.0,
        "elgato": 4.5,
        "playstation": 5.0,
        "xbox": 5.0,
        "nintendo": 5.0,
    }

    def analisar(self, oferta: Oferta) -> ResultadoCuradoriaComercial:
        motivos: list[str] = []

        pontos_categoria = self._calcular_categoria(oferta=oferta, motivos=motivos)

        marca, pontos_marca = self._calcular_marca(oferta=oferta, motivos=motivos)

        pontos_ticket = self._calcular_ticket(oferta=oferta, motivos=motivos)

        nota = pontos_categoria + pontos_marca + pontos_ticket

        nota = round(min(max(nota, 0.0), self.NOTA_MAXIMA), 2)

        return ResultadoCuradoriaComercial(
            nota=nota,
            marca=marca,
            pontos_categoria=round(pontos_categoria, 2),
            pontos_marca=round(pontos_marca, 2),
            pontos_ticket=round(pontos_ticket, 2),
            motivos=motivos,
        )

    def _calcular_categoria(self, oferta: Oferta, motivos: list[str]) -> float:
        categoria = oferta.categoria

        if not categoria:
            motivos.append("Categoria não identificada: +0.00")
            return 0.0

        pontos = self.PONTOS_CATEGORIAS.get(categoria, 2.0)

        motivos.append(f"Categoria {categoria}: +{pontos:.2f}")

        return pontos

    def _calcular_marca(self, oferta: Oferta, motivos: list[str]) -> tuple[str | None, float]:
        nome_normalizado = self._normalizar_texto(oferta.nome)

        marcas_ordenadas = sorted(
            self.PONTOS_MARCAS.items(), key=lambda item: len(item[0]), reverse=True
        )

        for marca, pontos in marcas_ordenadas:
            if self._contem_termo(texto=nome_normalizado, termo=marca):
                motivos.append(f"Marca {marca}: +{pontos:.2f}")

                return marca, pontos

        motivos.append("Marca prioritária não identificada: +0.00")

        return None, 0.0

    def _calcular_ticket(self, oferta: Oferta, motivos: list[str]) -> float:
        preco = oferta.preco

        if preco <= 0:
            motivos.append("Preço inválido: +0.00")
            return 0.0

        if preco < 30:
            pontos = 0.0
            faixa = "ticket muito baixo"

        elif preco < 50:
            pontos = 1.0
            faixa = "ticket baixo"

        elif preco <= 300:
            pontos = 4.0
            faixa = "ticket de alta conversão"

        elif preco <= 900:
            pontos = 5.0
            faixa = "ticket comercial ideal"

        elif preco <= 2000:
            pontos = 4.5
            faixa = "ticket médio-alto"

        elif preco <= 4000:
            pontos = 3.5
            faixa = "ticket alto"

        else:
            pontos = 2.0
            faixa = "ticket muito alto"

        motivos.append(f"{faixa}: +{pontos:.2f}")

        return pontos

    def _normalizar_texto(self, texto: str) -> str:
        texto_sem_acentos = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(caractere)
        )

        texto_normalizado = texto_sem_acentos.lower()

        texto_normalizado = re.sub(r"[^a-z0-9.+\- ]", " ", texto_normalizado)

        texto_normalizado = re.sub(r"\s+", " ", texto_normalizado)

        return texto_normalizado.strip()

    def _contem_termo(self, texto: str, termo: str) -> bool:
        termo_normalizado = self._normalizar_texto(termo)

        padrao = r"(?<![a-z0-9])" + re.escape(termo_normalizado) + r"(?![a-z0-9])"

        return re.search(padrao, texto) is not None
