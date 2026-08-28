# 63.8738, -149.7525

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True)
class ResultadoCuradoriaPublicacao:
    publicavel: bool
    nota: float
    motivos: tuple[str, ...]
    bloqueios: tuple[str, ...]


class CuradoriaPublicacao:
    """Decide se um produto válido merece disputar espaço no canal.

    O classificador responde "isso pertence ao universo do canal?".
    Esta camada responde uma pergunta diferente:
    "este anúncio é bom o suficiente e claro o bastante para entrar
    na fila de publicação automática?"

    Ela evita principalmente:
    - usados/recondicionados/defeituosos;
    - anúncios que parecem acessórios ou peças avulsas disfarçadas;
    - kits/combos ambíguos;
    - preços incompatíveis com a categoria, comuns em variações enganosas;
    - títulos excessivamente vagos.
    """

    NOTA_MAXIMA = 100.0

    TERMOS_CONDICAO_RISCO: tuple[str, ...] = (
        "usado",
        "usada",
        "seminovo",
        "seminova",
        "recondicionado",
        "recondicionada",
        "refurbished",
        "open box",
        "mostruario",
        "mostruário",
        "sucata",
        "com defeito",
        "defeito",
        "nao funciona",
        "não funciona",
        "para retirada de pecas",
        "para retirada de peças",
        "vencido",
        "vencida",
        "validade curta",
        "proximo do vencimento",
        "proximo do vencimento",
        "sem lacre",
        "lacre violado",
    )

    TERMOS_ACESSORIO_AMBIGUO: tuple[str, ...] = (
        "somente caixa",
        "apenas caixa",
        "caixa vazia",
        "carcaca",
        "carcaça",
        "placa para reparo",
        "kit reparo",
        "kit de reparo",
        "peca de reposicao",
        "peça de reposição",
        "display reposicao",
        "display reposição",
        "tela reposicao",
        "tela reposição",
        "placa filha",
    )

    PADROES_RUIDO_POR_CATEGORIA: dict[
        str,
        tuple[str, ...],
    ] = {
        "Placa de v?deo": (
            r"^(?:novo\s+|nova\s+)?(?:ventilador|fan|cooler)\b",
            r"^(?:novo\s+|nova\s+)?(?:capa|cover|caixa|malha)\b",
        ),
        "Suplementos": (
            r"^(?:coqueteleira|shaker|dosador|scoop|funil)\b",
            r"^(?:pote|embalagem)\s+vazi",
        ),
        "Caf\u00e9": (
            r"^(?:porta capsulas?|capsula reutilizavel|cafeteira|"
            r"moedor|filtro de cafe|caneca)\b",
        ),
        "Energ\u00e9ticos": (
            r"^(?:camiseta|camisa|bone|adesivo|placa decorativa|"
            r"copo|caneca|porta lata|porta-lata|suporte para lata|"
            r"abridor|garrafa|squeeze)\b",
        ),
        "Chocolate e snacks": (r"^(?:forma|molde|essencia|aroma|corante)\b.*\bchocolate\b",),
    }
    TERMOS_KIT_COMBO: tuple[str, ...] = (
        "kit",
        "combo",
        "lote",
        "atacado",
    )

    CATEGORIAS_ONDE_KIT_E_NORMAL: frozenset[str] = frozenset(
        {
            "Maker e bancada",
            "Suportes e conectividade",
            "Iluminação de setup",
            "Suplementos",
            "Energ\u00e9ticos",
            "Caf\u00e9",
            "Chocolate e snacks",
        }
    )

    # Piso propositalmente conservador. Abaixo disso, a chance de ser
    # acessório, parcela, variação diferente ou título enganoso é alta.
    # Preço anômalo real com histórico continua sendo tratado pela camada
    # específica de anomalias; primeiro registro suspeito não vai ao canal.
    PRECO_MINIMO_PLAUSIVEL: dict[str, float] = {
        "Placa de vídeo": 250.0,
        "Processador": 120.0,
        "Placa-mãe": 180.0,
        "Memória RAM": 50.0,
        "Armazenamento": 35.0,
        "Fonte e energia": 45.0,
        "Gabinete": 100.0,
        "Refrigeração de PC": 25.0,
        "Monitor": 250.0,
        "TV": 500.0,
        "Projetor": 120.0,
        "Celular": 250.0,
        "Tablet e e-reader": 250.0,
        "Notebook": 700.0,
        "Computador e Mini PC": 550.0,
        "Console": 700.0,
        "Realidade virtual": 700.0,
        "Mobiliário e ergonomia": 150.0,
        "Climatização e conforto": 40.0,
        "Suplementos": 5.0,
        "Energ\u00e9ticos": 3.0,
        "Caf\u00e9": 5.0,
        "Chocolate e snacks": 2.0,
    }

    def __init__(self, nota_minima: float = 55.0, ativa: bool = True) -> None:
        if not 0 <= nota_minima <= self.NOTA_MAXIMA:
            raise ValueError("nota_minima precisa estar entre 0 e 100.")

        self.nota_minima = nota_minima
        self.ativa = ativa

    def analisar(self, oferta: Oferta) -> ResultadoCuradoriaPublicacao:
        if not self.ativa:
            resultado = ResultadoCuradoriaPublicacao(
                publicavel=True,
                nota=100.0,
                motivos=("Curadoria de publicação desativada.",),
                bloqueios=(),
            )
            self._aplicar(oferta, resultado)
            return resultado

        texto = self._normalizar(oferta.nome)

        nota = 70.0
        motivos: list[str] = []
        bloqueios: list[str] = []

        if len(texto) < 8:
            bloqueios.append("Título curto demais para identificar o produto.")

        riscos_condicao = self._encontrar(texto, self.TERMOS_CONDICAO_RISCO)

        if riscos_condicao:
            bloqueios.append(
                "Condição não adequada para publicação automática: "
                + ", ".join(riscos_condicao)
                + "."
            )

        riscos_acessorio = self._encontrar(texto, self.TERMOS_ACESSORIO_AMBIGUO)

        if riscos_acessorio:
            bloqueios.append(
                "Anúncio parece peça/acessório ambíguo: " + ", ".join(riscos_acessorio) + "."
            )

        padroes_ruido_categoria = self.PADROES_RUIDO_POR_CATEGORIA.get(
            oferta.categoria or "",
            (),
        )

        if any(re.search(padrao, texto) for padrao in padroes_ruido_categoria):
            bloqueios.append(
                "Anuncio parece ser acessorio, embalagem ou item " "associado ao produto principal."
            )

        if oferta.preco <= 0:
            bloqueios.append("Preço inválido.")

        piso = self.PRECO_MINIMO_PLAUSIVEL.get(oferta.categoria or "")

        if piso is not None and 0 < oferta.preco < piso:
            bloqueios.append(
                f"Preço de {oferta.moeda} {oferta.preco:.2f} é incompatível "
                f"com o piso conservador de {oferta.moeda} {piso:.2f} "
                f"para {oferta.categoria}."
            )

        if oferta.eh_nicho:
            nota += 8.0
            motivos.append("Produto pertence ao nicho monitorado: +8.")

        if oferta.relevancia_nicho >= 80:
            nota += 8.0
            motivos.append("Classificação de nicho forte: +8.")
        elif oferta.relevancia_nicho < 60:
            nota -= 12.0
            motivos.append("Classificação de nicho fraca: -12.")

        if oferta.confianca_normalizacao >= 90:
            nota += 8.0
            motivos.append("Modelo identificado com alta confiança: +8.")
        elif oferta.confianca_normalizacao < 50:
            nota -= 4.0
            motivos.append("Identidade do produto pouco precisa: -4.")

        termos_kit = self._encontrar(texto, self.TERMOS_KIT_COMBO)

        if termos_kit and oferta.categoria not in self.CATEGORIAS_ONDE_KIT_E_NORMAL:
            nota -= 18.0
            motivos.append("Kit/combo/lote reduz clareza para comparação de preço: -18.")

        if oferta.desconto_percentual >= 10:
            nota += 4.0
            motivos.append("Há desconto anunciado mensurável: +4.")

        if oferta.preco_antigo is not None and oferta.preco_antigo <= oferta.preco:
            nota -= 4.0
            motivos.append("Preço antigo não confirma desconto real: -4.")

        nota = round(min(max(nota, 0.0), self.NOTA_MAXIMA), 2)

        publicavel = not bloqueios and nota >= self.nota_minima

        if not bloqueios and nota < self.nota_minima:
            motivos.append(f"Nota {nota:.1f}/100 abaixo da mínima {self.nota_minima:.1f}/100.")

        resultado = ResultadoCuradoriaPublicacao(
            publicavel=publicavel,
            nota=nota,
            motivos=tuple(motivos),
            bloqueios=tuple(bloqueios),
        )

        self._aplicar(oferta, resultado)

        return resultado

    @staticmethod
    def _aplicar(oferta: Oferta, resultado: ResultadoCuradoriaPublicacao) -> None:
        oferta.curadoria_publicavel = resultado.publicavel
        oferta.nota_curadoria = resultado.nota
        oferta.motivos_curadoria = list(resultado.bloqueios + resultado.motivos)

    @classmethod
    def _encontrar(cls, texto: str, termos: tuple[str, ...]) -> list[str]:
        encontrados: list[str] = []

        for termo in termos:
            termo_normalizado = cls._normalizar(termo)
            padrao = r"(?<![a-z0-9])" + re.escape(termo_normalizado) + r"(?![a-z0-9])"

            if re.search(padrao, texto):
                encontrados.append(termo)

        return encontrados

    @staticmethod
    def _normalizar(texto: str) -> str:
        sem_acentos = "".join(
            caractere
            for caractere in unicodedata.normalize("NFKD", texto)
            if not unicodedata.combining(caractere)
        )

        sem_acentos = sem_acentos.lower()
        sem_acentos = re.sub(r"[^a-z0-9+\- ]", " ", sem_acentos)
        sem_acentos = re.sub(r"\s+", " ", sem_acentos)

        return sem_acentos.strip()
