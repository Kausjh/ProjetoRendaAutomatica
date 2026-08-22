# 63.8738, -149.7525

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True)
class ResultadoNormalizacaoProduto:
    nome_canonico: str
    chave_canonica: str
    modelo: str | None
    confianca: float
    estrategia: str


class NormalizadorProduto:
    """Cria identidade canônica sem confundir produto principal com componente.

    Uma RTX citada dentro de um notebook não transforma o notebook em "RTX
    4050". Modelos de CPU/GPU só recebem confiança alta quando a categoria
    principal também é CPU/GPU. Produtos compostos usam fallback conservador
    e, portanto, não entram na deduplicação automática de alta confiança.
    """

    PADROES_GPU: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("nvidia_rtx", re.compile(r"\brtx\s*(?P<modelo>\d{4}(?:\s*ti|\s*super)?)\b", re.I)),
        ("nvidia_gtx", re.compile(r"\bgtx\s*(?P<modelo>\d{3,4}(?:\s*ti|\s*super)?)\b", re.I)),
        ("amd_rx", re.compile(r"\brx\s*(?P<modelo>\d{3,4}(?:\s*xt|\s*xtx)?)\b", re.I)),
    )

    PADROES_CPU: tuple[tuple[str, re.Pattern[str]], ...] = (
        (
            "amd_ryzen",
            re.compile(r"\bryzen\s*(?P<linha>[3579])\s*(?P<modelo>\d{4}[a-z0-9]*)\b", re.I),
        ),
        (
            "intel_core",
            re.compile(
                r"\b(?:intel\s*)?core\s*i(?P<linha>[3579])[-\s]*(?P<modelo>\d{4,5}[a-z]{0,2})\b",
                re.I,
            ),
        ),
    )

    PADROES_DISPOSITIVOS: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("playstation", re.compile(r"\b(?:playstation|ps)\s*(?P<modelo>[45])\b", re.I)),
        ("xbox_series", re.compile(r"\bxbox\s*series\s*(?P<modelo>[sx])\b", re.I)),
        (
            "galaxy_s",
            re.compile(r"\bgalaxy\s*s(?P<modelo>\d{2}(?:\s*(?:fe|plus|ultra))?)\b", re.I),
        ),
        (
            "iphone",
            re.compile(r"\biphone\s*(?P<modelo>\d{2}(?:\s*(?:pro|max|plus|mini)){0,2})\b", re.I),
        ),
    )

    CATEGORIAS_COMPOSTAS: frozenset[str] = frozenset(
        {"Notebook", "Computador e Mini PC", "Kit upgrade"}
    )

    PALAVRAS_RUIDO: frozenset[str] = frozenset(
        {
            "novo",
            "nova",
            "original",
            "lacrado",
            "lacrada",
            "oficial",
            "promocao",
            "oferta",
            "envio",
            "imediato",
            "pronta",
            "entrega",
            "frete",
            "gratis",
            "com",
            "para",
            "de",
            "do",
            "da",
            "e",
        }
    )

    def normalizar(self, oferta: Oferta) -> ResultadoNormalizacaoProduto:
        texto = self._normalizar_texto(oferta.nome)
        categoria = oferta.categoria or ""

        modelo: tuple[str, str, str] | None = None

        if categoria == "Placa de vídeo":
            modelo = self._extrair_gpu(texto)
        elif categoria == "Processador":
            modelo = self._extrair_cpu(texto)
        elif categoria in {"Console", "Celular"}:
            if self._dispositivo_pode_ser_canonizado(
                texto=texto,
                categoria=categoria,
            ):
                modelo = self._extrair_dispositivo(texto)

        if modelo is not None:
            nome_canonico, chave, estrategia = modelo
            resultado = ResultadoNormalizacaoProduto(
                nome_canonico=nome_canonico,
                chave_canonica=chave,
                modelo=nome_canonico,
                confianca=95.0,
                estrategia=estrategia,
            )
        else:
            nome_canonico = self._criar_fallback(oferta=oferta, texto=texto)
            resultado = ResultadoNormalizacaoProduto(
                nome_canonico=nome_canonico,
                chave_canonica=self._slug(nome_canonico),
                modelo=None,
                confianca=35.0 if categoria in self.CATEGORIAS_COMPOSTAS else 45.0,
                estrategia="fallback_contextual_conservador",
            )

        oferta.produto_canonico = resultado.nome_canonico
        oferta.chave_produto_canonica = resultado.chave_canonica
        oferta.modelo_produto = resultado.modelo
        oferta.confianca_normalizacao = resultado.confianca
        return resultado

    def _dispositivo_pode_ser_canonizado(
        self,
        texto: str,
        categoria: str,
    ) -> bool:
        if categoria == "Console":
            termos_acessorio = (
                "headset",
                "fone",
                "ssd",
                "nvme",
                "controle",
                "gamepad",
                "joystick",
                "suporte",
                "base",
                "dock",
                "cabo",
                "carregador",
                "adaptador",
                "capa",
                "skin",
                "volante",
                "pedal",
                "mouse",
                "teclado",
                "microfone",
                "placa de captura",
            )

            if any(self._contem_termo(texto, termo) for termo in termos_acessorio):
                return False

            if re.search(
                r"\b(?:para|compativel com|funciona (?:no|em))\s+"
                r"(?:o\s+)?(?:ps4|ps5|playstation|xbox)\b",
                texto,
            ):
                return False

        if categoria == "Celular":
            for termo in (
                "capa",
                "capinha",
                "pelicula",
                "carregador",
                "cabo",
                "suporte",
                "bateria",
                "tela",
                "display",
            ):
                if self._contem_termo(texto, termo):
                    return False

        return True

    @staticmethod
    def _contem_termo(texto: str, termo: str) -> bool:
        termo_normalizado = NormalizadorProduto._normalizar_texto(termo)
        padrao = r"(?<![a-z0-9])" + re.escape(termo_normalizado) + r"(?![a-z0-9])"
        return re.search(padrao, texto) is not None

    def _extrair_gpu(self, texto: str) -> tuple[str, str, str] | None:
        for nome_padrao, padrao in self.PADROES_GPU:
            match = padrao.search(texto)
            if match is None:
                continue
            modelo = self._normalizar_sufixo(match.group("modelo")).upper()
            if nome_padrao == "nvidia_rtx":
                nome = f"RTX {modelo}"
            elif nome_padrao == "nvidia_gtx":
                nome = f"GTX {modelo}"
            else:
                nome = f"RX {modelo}"
            return nome, self._slug(nome), nome_padrao
        return None

    def _extrair_cpu(self, texto: str) -> tuple[str, str, str] | None:
        for nome_padrao, padrao in self.PADROES_CPU:
            match = padrao.search(texto)
            if match is None:
                continue
            if nome_padrao == "amd_ryzen":
                nome = f"Ryzen {match.group('linha')} {match.group('modelo').upper()}"
            else:
                nome = f"Core i{match.group('linha')}-{match.group('modelo').upper()}"
            return nome, self._slug(nome), nome_padrao
        return None

    def _extrair_dispositivo(self, texto: str) -> tuple[str, str, str] | None:
        for nome_padrao, padrao in self.PADROES_DISPOSITIVOS:
            match = padrao.search(texto)
            if match is None:
                continue
            modelo = self._normalizar_sufixo(match.group("modelo"))
            if nome_padrao == "playstation":
                nome = f"PlayStation {modelo}"
            elif nome_padrao == "xbox_series":
                nome = f"Xbox Series {modelo.upper()}"
            elif nome_padrao == "galaxy_s":
                nome = f"Galaxy S{modelo.upper()}"
            else:
                nome = f"iPhone {modelo.title()}"
            return nome, self._slug(nome), nome_padrao
        return None

    def _criar_fallback(self, oferta: Oferta, texto: str) -> str:
        tokens = [
            token for token in texto.split() if token not in self.PALAVRAS_RUIDO and len(token) > 1
        ]
        selecionados = tokens[:10]
        prefixo = oferta.categoria or "Produto"
        if not selecionados:
            return prefixo
        return f"{prefixo}: {' '.join(selecionados)}"

    @staticmethod
    def _normalizar_sufixo(valor: str) -> str:
        return re.sub(r"\s+", " ", valor.strip())

    @staticmethod
    def _slug(texto: str) -> str:
        return NormalizadorProduto._normalizar_texto(texto).replace(" ", "_")

    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        sem_acentos = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(caractere)
        )
        sem_acentos = sem_acentos.lower()
        sem_acentos = re.sub(r"[^a-z0-9+\- ]", " ", sem_acentos)
        sem_acentos = re.sub(r"\s+", " ", sem_acentos)
        return sem_acentos.strip()
