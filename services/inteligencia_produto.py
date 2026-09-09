# 63.8738, -149.7525

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True)
class ResultadoInteligenciaProduto:
    nota: float
    confianca: float
    nivel: str
    categoria: str | None
    marca: str | None
    modelo: str | None
    familia: str | None
    pontos_categoria: float
    pontos_modelo: float
    pontos_marca: float
    pontos_identidade: float
    motivos: tuple[str, ...]


class InteligenciaProduto:
    """Mede desejabilidade intrinseca do produto.

    Nao usa preco, desconto, cupom ou historico.

    Product Quality != Deal Quality.
    """

    NOTA_MAXIMA = 100.0

    PONTOS_CATEGORIAS = {
        "placa de video": 30.0,
        "processador": 30.0,
        "notebook gamer": 27.0,
        "computador gamer": 25.0,
        "monitor": 24.0,
        "placa mae": 22.0,
        "memoria ram": 20.0,
        "armazenamento": 18.0,
        "fonte": 18.0,
        "refrigeracao": 16.0,
        "console": 22.0,
        "headset e audio": 14.0,
        "teclado": 12.0,
        "mouse": 12.0,
        "controle": 12.0,
        "streaming e captura": 15.0,
        "simulacao": 15.0,
        "rede": 10.0,
        "gabinete": 10.0,
        "mobiliario gamer": 8.0,
    }

    PADROES_MODELO = (
        # NVIDIA 50
        (r"\brtx\s*5090\b", "RTX 5090", 40.0),
        (r"\brtx\s*5080\b", "RTX 5080", 40.0),
        (
            r"\brtx\s*5070\s*ti\b",
            "RTX 5070 Ti",
            39.0,
        ),
        (r"\brtx\s*5070\b", "RTX 5070", 38.0),
        (
            r"\brtx\s*5060\s*ti\b",
            "RTX 5060 Ti",
            37.0,
        ),
        (r"\brtx\s*5060\b", "RTX 5060", 36.0),
        # NVIDIA 40
        (r"\brtx\s*4090\b", "RTX 4090", 39.0),
        (
            r"\brtx\s*4080\s*super\b",
            "RTX 4080 Super",
            38.0,
        ),
        (
            r"\brtx\s*4070\s*ti\s*super\b",
            "RTX 4070 Ti Super",
            37.0,
        ),
        (
            r"\brtx\s*4070\s*super\b",
            "RTX 4070 Super",
            35.0,
        ),
        (r"\brtx\s*4070\b", "RTX 4070", 33.0),
        (
            r"\brtx\s*4060\s*ti\b",
            "RTX 4060 Ti",
            29.0,
        ),
        (r"\brtx\s*4060\b", "RTX 4060", 26.0),
        # AMD GPU
        (
            r"\brx\s*9070\s*xt\b",
            "RX 9070 XT",
            39.0,
        ),
        (
            r"\brx\s*9060\s*xt\b",
            "RX 9060 XT",
            35.0,
        ),
        (r"\brx\s*9070\b", "RX 9070", 37.0),
        (
            r"\brx\s*7900\s*xtx\b",
            "RX 7900 XTX",
            37.0,
        ),
        (
            r"\brx\s*7900\s*xt\b",
            "RX 7900 XT",
            35.0,
        ),
        (
            r"\brx\s*7800\s*xt\b",
            "RX 7800 XT",
            32.0,
        ),
        (
            r"\brx\s*7700\s*xt\b",
            "RX 7700 XT",
            29.0,
        ),
        # AMD CPU
        (
            r"\bryzen\s*9\s*9950x3d\b",
            "Ryzen 9 9950X3D",
            40.0,
        ),
        (
            r"\bryzen\s*7\s*9800x3d\b",
            "Ryzen 7 9800X3D",
            40.0,
        ),
        (
            r"\bryzen\s*7\s*7800x3d\b",
            "Ryzen 7 7800X3D",
            39.0,
        ),
        (
            r"\bryzen\s*7\s*5800x3d\b",
            "Ryzen 7 5800X3D",
            36.0,
        ),
        (
            r"\bryzen\s*7\s*5700x3d\b",
            "Ryzen 7 5700X3D",
            35.0,
        ),
        (
            r"\bryzen\s*7\s*5700x\b",
            "Ryzen 7 5700X",
            34.0,
        ),
        (
            r"\bryzen\s*7\s*9700x\b",
            "Ryzen 7 9700X",
            36.0,
        ),
        (
            r"\bryzen\s*7\s*7700\b",
            "Ryzen 7 7700",
            32.0,
        ),
        (
            r"\bryzen\s*5\s*9600x\b",
            "Ryzen 5 9600X",
            33.0,
        ),
        (
            r"\bryzen\s*5\s*7600\b",
            "Ryzen 5 7600",
            31.0,
        ),
        (
            r"\bryzen\s*5\s*5600gt\b",
            "Ryzen 5 5600GT",
            27.0,
        ),
        (
            r"\bryzen\s*5\s*5600\b",
            "Ryzen 5 5600",
            29.0,
        ),
        (
            r"\bryzen\s*5\s*5500\b",
            "Ryzen 5 5500",
            24.0,
        ),
        # Intel
        (
            r"\bcore\s*ultra\s*9\s*285k\b",
            "Core Ultra 9 285K",
            38.0,
        ),
        (
            r"\bcore\s*ultra\s*7\s*265k\b",
            "Core Ultra 7 265K",
            35.0,
        ),
        (
            r"\bi9[\s-]*14900k\b",
            "Core i9-14900K",
            35.0,
        ),
        (
            r"\bi7[\s-]*14700k\b",
            "Core i7-14700K",
            32.0,
        ),
        # Monitores
        (r"\bultragear\b", "LG UltraGear", 34.0),
        (
            r"\bodyssey\s*g9\b",
            "Samsung Odyssey G9",
            38.0,
        ),
        (
            r"\bodyssey\s*g8\b",
            "Samsung Odyssey G8",
            36.0,
        ),
        (
            r"\bodyssey\s*g7\b",
            "Samsung Odyssey G7",
            34.0,
        ),
        (
            r"\bodyssey\s*g6\b",
            "Samsung Odyssey G6",
            32.0,
        ),
        (
            r"\bodyssey\s*g5\b",
            "Samsung Odyssey G5",
            30.0,
        ),
        (r"\bevnia\b", "Philips Evnia", 30.0),
        # Placas-mae
        (r"\bx870e?\b", "X870", 31.0),
        (r"\bb850\b", "B850", 29.0),
        (r"\bx670e?\b", "X670", 28.0),
        (r"\bb650e?\b", "B650", 27.0),
        (r"\bb550m?\b", "B550", 24.0),
        (r"\bz790\b", "Z790", 28.0),
        # SSD
        (
            r"\b990\s*pro\b",
            "Samsung 990 PRO",
            34.0,
        ),
        (
            r"\b980\s*pro\b",
            "Samsung 980 PRO",
            29.0,
        ),
        (
            r"\bsn850x\b",
            "WD Black SN850X",
            32.0,
        ),
        (
            r"\bkc3000\b",
            "Kingston KC3000",
            29.0,
        ),
        # Outros
        (
            r"\bcore\s*reactor\b",
            "XPG Core Reactor",
            30.0,
        ),
        (
            r"\bmwe\s*gold\b",
            "Cooler Master MWE Gold",
            27.0,
        ),
        (
            r"\bredragon\s*zeus\b",
            "Redragon Zeus",
            23.0,
        ),
        (
            r"\bhavit\s*fuxi\b",
            "Havit Fuxi",
            22.0,
        ),
    )

    MARCAS = (
        ("nvidia", "NVIDIA", 20.0),
        ("amd", "AMD", 20.0),
        ("intel", "Intel", 20.0),
        ("asus", "ASUS", 20.0),
        ("aorus", "Gigabyte AORUS", 19.0),
        ("gigabyte", "Gigabyte", 19.0),
        ("msi", "MSI", 19.0),
        ("samsung", "Samsung", 20.0),
        ("lg", "LG", 18.0),
        ("kingston", "Kingston", 18.0),
        (
            "western digital",
            "Western Digital",
            18.0,
        ),
        ("wd", "Western Digital", 17.0),
        ("corsair", "Corsair", 18.0),
        ("crucial", "Crucial", 17.0),
        ("xpg", "XPG", 16.0),
        (
            "cooler master",
            "Cooler Master",
            17.0,
        ),
        ("logitech", "Logitech", 18.0),
        ("hyperx", "HyperX", 17.0),
        ("razer", "Razer", 17.0),
        ("aoc", "AOC", 16.0),
        ("philips", "Philips", 15.0),
        ("acer", "Acer", 15.0),
        ("dell", "Dell", 16.0),
        ("lenovo", "Lenovo", 15.0),
        ("tuf", "ASUS TUF", 18.0),
        ("redragon", "Redragon", 13.0),
        ("havit", "Havit", 12.0),
    )

    def analisar(
        self,
        oferta: Oferta,
    ) -> ResultadoInteligenciaProduto:
        texto = self._normalizar(
            " ".join(
                parte
                for parte in (
                    oferta.nome,
                    oferta.produto_canonico,
                    oferta.modelo_produto,
                    oferta.familia_produto,
                )
                if parte
            )
        )

        categoria = oferta.categoria

        pontos_categoria = self._pontos_categoria(categoria)

        modelo, pontos_modelo = self._detectar_modelo(texto)

        marca, pontos_marca = self._detectar_marca(texto)

        confianca = self._calcular_confianca(
            oferta=oferta,
            categoria=categoria,
            marca=marca,
            modelo=modelo,
        )

        pontos_identidade = confianca / 100.0 * 10.0

        nota = round(
            min(
                max(
                    pontos_categoria + pontos_modelo + pontos_marca + pontos_identidade,
                    0.0,
                ),
                self.NOTA_MAXIMA,
            ),
            2,
        )

        nivel = self._nivel(nota)

        motivos = (
            ("categoria=" f"{categoria or 'nao_identificada'}:" f"{pontos_categoria:.1f}"),
            ("modelo=" f"{modelo or 'nao_identificado'}:" f"{pontos_modelo:.1f}"),
            ("marca=" f"{marca or 'nao_identificada'}:" f"{pontos_marca:.1f}"),
            (f"identidade={confianca:.1f}:" f"{pontos_identidade:.1f}"),
        )

        return ResultadoInteligenciaProduto(
            nota=nota,
            confianca=round(
                confianca,
                2,
            ),
            nivel=nivel,
            categoria=categoria,
            marca=marca,
            modelo=modelo,
            familia=modelo,
            pontos_categoria=round(
                pontos_categoria,
                2,
            ),
            pontos_modelo=round(
                pontos_modelo,
                2,
            ),
            pontos_marca=round(
                pontos_marca,
                2,
            ),
            pontos_identidade=round(
                pontos_identidade,
                2,
            ),
            motivos=motivos,
        )

    def aplicar(
        self,
        oferta: Oferta,
    ) -> ResultadoInteligenciaProduto:
        resultado = self.analisar(oferta)

        oferta.nota_produto = resultado.nota

        oferta.confianca_produto = resultado.confianca

        oferta.nivel_desejabilidade = resultado.nivel

        oferta.motivos_produto = list(resultado.motivos)

        if not oferta.modelo_produto and resultado.modelo:
            oferta.modelo_produto = resultado.modelo

        if not oferta.familia_produto and resultado.familia:
            oferta.familia_produto = resultado.familia

        return resultado

    def _pontos_categoria(
        self,
        categoria: str | None,
    ) -> float:
        if not categoria:
            return 0.0

        chave = self._normalizar(categoria)

        return float(
            self.PONTOS_CATEGORIAS.get(
                chave,
                5.0,
            )
        )

    def _detectar_modelo(
        self,
        texto: str,
    ) -> tuple[str | None, float]:
        for (
            padrao,
            modelo,
            pontos,
        ) in self.PADROES_MODELO:
            if re.search(
                padrao,
                texto,
            ):
                return (
                    modelo,
                    pontos,
                )

        return (
            None,
            0.0,
        )

    def _detectar_marca(
        self,
        texto: str,
    ) -> tuple[str | None, float]:
        texto_cercado = f" {texto} "

        melhor = (
            None,
            0.0,
        )

        for (
            termo,
            marca,
            pontos,
        ) in self.MARCAS:
            termo = self._normalizar(termo)

            if f" {termo} " not in texto_cercado:
                continue

            if pontos > melhor[1]:
                melhor = (
                    marca,
                    pontos,
                )

        return melhor

    @staticmethod
    def _calcular_confianca(
        *,
        oferta: Oferta,
        categoria: str | None,
        marca: str | None,
        modelo: str | None,
    ) -> float:
        confianca = max(
            float(oferta.confianca_normalizacao or 0.0),
            float(oferta.confianca_familia or 0.0),
        )

        if modelo:
            confianca = max(
                confianca,
                96.0,
            )

        elif marca and categoria:
            confianca = max(
                confianca,
                80.0,
            )

        elif categoria:
            confianca = max(
                confianca,
                55.0,
            )

        elif oferta.eh_nicho:
            confianca = max(
                confianca,
                25.0,
            )

        return min(
            max(
                confianca,
                0.0,
            ),
            100.0,
        )

    @staticmethod
    def _nivel(
        nota: float,
    ) -> str:
        if nota >= 85.0:
            return "muito_alto"

        if nota >= 70.0:
            return "alto"

        if nota >= 50.0:
            return "medio"

        return "baixo"

    @staticmethod
    def _normalizar(
        valor: str,
    ) -> str:
        texto = unicodedata.normalize(
            "NFKD",
            str(valor or ""),
        )

        texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))

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
