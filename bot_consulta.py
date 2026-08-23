# 63.8738, -149.7525

"""Bot de consulta ao histórico de preços.

Programa independente do pipeline de publicação. Fica escutando
mensagens no Telegram e responde usando somente o histórico que o
pipeline já gravou em disco.

Não depende de Chrome/CDP e não dispara scrapers.

Execução:
    python bot_consulta.py

Principais recursos:
    - busca livre por produto;
    - aliases conservadores de modelos/linhas;
    - /menorpreco <produto>;
    - /historico <produto>;
    - /categoria <categoria>;
    - /categorias;
    - comparação por texto: produto A vs produto B.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from statistics import mean
from typing import Any

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config.configuracoes import Configuracoes
from config.logging_config import configurar_logging

configurar_logging()

logger = logging.getLogger(__name__)

CAMINHO_HISTORICO = Path("data/historico/mercado_livre_precos.json")

LIMITE_RESULTADOS = 4
LIMITE_RESULTADOS_CATEGORIA = 8
LIMITE_PONTOS_HISTORICO = 8
MINIMO_CARACTERES_BUSCA = 3

# Abaixo destes limites o histórico é curto demais para afirmar
# que um preço é o melhor de todos os tempos.
DIAS_PARA_HISTORICO_CONFIAVEL = 30
REGISTROS_PARA_HISTORICO_CONFIAVEL = 10

LINK_CANAL = "https://t.me/CanalRadarDeOfertasBR"

# Aliases deliberadamente conservadores. A ideia é facilitar buscas
# comuns sem transformar palavras genéricas em outra coisa.
ALIASES_TOKEN = {
    "r5": ("ryzen", "5"),
    "r7": ("ryzen", "7"),
    "r9": ("ryzen", "9"),
}

ALIASES_FRASE = {
    "play station": "playstation",
    "ps 5": "ps5",
    "ps 4": "ps4",
    "wi fi": "wifi",
    "m 2": "m2",
    "usb c": "usb c",
}


CATEGORIAS_CANONICAS = {
    "fonte": "Fonte e energia",
    "fonte e energia": "Fonte e energia",
    "audio": "Áudio",
    "eletronicos audio e video": "Áudio e vídeo",
    "audio e video": "Áudio e vídeo",
    "headset e audio": "Headset e áudio",
    "mouse": "Mouse e mousepad",
    "mouse e mousepad": "Mouse e mousepad",
    "notebook": "Notebook",
    "notebook gamer": "Notebook",
    "computador gamer": "Computador gamer",
}


@dataclass(frozen=True)
class PontoHistorico:
    preco: float
    coletado_em: str


@dataclass(frozen=True)
class ResumoProduto:
    chave: str
    titulo: str
    link: str
    categoria: str
    preco_atual: float
    menor_preco: float
    maior_preco: float
    preco_medio: float
    quantidade_registros: int
    primeiro_registro_em: str
    esta_no_menor_preco: bool
    dias_de_acompanhamento: int

    @property
    def historico_e_confiavel(self) -> bool:
        """Indica se já há dados suficientes para conclusões fortes."""

        return (
            self.dias_de_acompanhamento >= DIAS_PARA_HISTORICO_CONFIAVEL
            and self.quantidade_registros >= REGISTROS_PARA_HISTORICO_CONFIAVEL
        )

    @property
    def distancia_do_menor_percentual(self) -> float:
        if self.menor_preco <= 0:
            return 0.0

        return max(((self.preco_atual / self.menor_preco) - 1) * 100, 0.0)

    @property
    def distancia_da_media_percentual(self) -> float:
        if self.preco_medio <= 0:
            return 0.0

        return ((self.preco_atual / self.preco_medio) - 1) * 100


class ConsultaHistorico:
    """Lê o histórico de preços e responde consultas."""

    def __init__(self, caminho: Path = CAMINHO_HISTORICO) -> None:
        self.caminho = caminho
        self._dados: dict[str, Any] = {"produtos": {}}
        self._carregado_em: float = 0.0

    def _carregar_se_necessario(self) -> None:
        """Recarrega o arquivo quando o pipeline o atualiza."""

        if not self.caminho.exists():
            self._dados = {"produtos": {}}
            return

        modificado_em = self.caminho.stat().st_mtime

        if modificado_em == self._carregado_em:
            return

        try:
            with self.caminho.open("r", encoding="utf-8") as arquivo:
                self._dados = json.load(arquivo)

            self._carregado_em = modificado_em

            logger.info(
                "Histórico recarregado: %s produto(s).",
                len(self._dados.get("produtos", {})),
            )

        except (json.JSONDecodeError, OSError):
            logger.exception("Não foi possível carregar o histórico de preços.")

    def quantidade_produtos(self) -> int:
        self._carregar_se_necessario()

        return len(self._dados.get("produtos", {}))

    def buscar(
        self,
        termo: str,
        limite: int = LIMITE_RESULTADOS,
    ) -> list[ResumoProduto]:
        self._carregar_se_necessario()

        termo_normalizado = normalizar_busca(termo)

        if len(termo_normalizado) < MINIMO_CARACTERES_BUSCA:
            return []

        palavras = [palavra for palavra in termo_normalizado.split() if palavra]

        encontrados: list[tuple[float, ResumoProduto]] = []

        for chave, produto in self._iterar_produtos():
            titulo = str(produto.get("titulo") or "")
            titulo_normalizado = normalizar_busca(titulo)

            acertos = sum(1 for palavra in palavras if contem_palavra(titulo_normalizado, palavra))

            if acertos < len(palavras):
                # Exige que o título contenha todos os termos buscados.
                continue

            resumo = self._montar_resumo(chave, produto)

            if resumo is None:
                continue

            relevancia = self._calcular_relevancia(
                titulo_normalizado=titulo_normalizado,
                termo_normalizado=termo_normalizado,
                palavras=palavras,
            )

            encontrados.append((relevancia, resumo))

        encontrados.sort(
            key=lambda item: (
                item[0],
                item[1].quantidade_registros,
            ),
            reverse=True,
        )

        return [resumo for _, resumo in encontrados[:limite]]

    def buscar_por_categoria(
        self,
        termo_categoria: str,
        limite: int = LIMITE_RESULTADOS_CATEGORIA,
    ) -> list[ResumoProduto]:
        self._carregar_se_necessario()

        termo_normalizado = normalizar(canonizar_categoria(termo_categoria))
        palavras = [palavra for palavra in termo_normalizado.split() if palavra]

        if not palavras:
            return []

        encontrados: list[ResumoProduto] = []

        for chave, produto in self._iterar_produtos():
            categoria_original = str(produto.get("categoria") or "")
            categoria = normalizar(canonizar_categoria(categoria_original))

            if not categoria:
                continue

            if not all(contem_palavra(categoria, palavra) for palavra in palavras):
                continue

            resumo = self._montar_resumo(chave, produto)

            if resumo is not None:
                encontrados.append(resumo)

        encontrados.sort(
            key=lambda resumo: (
                resumo.esta_no_menor_preco,
                -resumo.distancia_do_menor_percentual,
                resumo.quantidade_registros,
            ),
            reverse=True,
        )

        return encontrados[:limite]

    def listar_categorias(self) -> list[tuple[str, int]]:
        self._carregar_se_necessario()

        contagem: dict[str, int] = {}

        for _, produto in self._iterar_produtos():
            categoria_original = str(produto.get("categoria") or "").strip()

            if not categoria_original:
                continue

            categoria = canonizar_categoria(categoria_original)
            contagem[categoria] = contagem.get(categoria, 0) + 1

        return sorted(
            contagem.items(),
            key=lambda item: (-item[1], normalizar(item[0])),
        )

    def obter_pontos_historico(
        self,
        chave: str,
        limite: int = LIMITE_PONTOS_HISTORICO,
    ) -> list[PontoHistorico]:
        self._carregar_se_necessario()

        produto = self._dados.get("produtos", {}).get(chave)

        if not isinstance(produto, dict):
            return []

        registros = produto.get("registros") or []

        pontos: list[PontoHistorico] = []

        for registro in registros:
            if not isinstance(registro, dict):
                continue

            preco = registro.get("preco")

            if isinstance(preco, bool) or not isinstance(preco, (int, float)):
                continue

            pontos.append(
                PontoHistorico(
                    preco=float(preco),
                    coletado_em=str(registro.get("coletado_em") or ""),
                )
            )

        return pontos[-limite:]

    def _iterar_produtos(self) -> Iterable[tuple[str, dict[str, Any]]]:
        produtos = self._dados.get("produtos", {})

        if not isinstance(produtos, dict):
            return []

        return (
            (str(chave), produto)
            for chave, produto in produtos.items()
            if isinstance(produto, dict)
        )

    def _calcular_relevancia(
        self,
        titulo_normalizado: str,
        termo_normalizado: str,
        palavras: list[str],
    ) -> float:
        """Prioriza o produto em si, não combos que apenas citam o termo."""

        relevancia = float(len(palavras))

        # A expressão completa aparecendo na ordem indica correspondência direta.
        if termo_normalizado in titulo_normalizado:
            relevancia += 3.0

        palavras_titulo = titulo_normalizado.split()

        # Título enxuto tende a ser o produto puro; título longo costuma
        # ser kit, combo ou anúncio com vários itens.
        if palavras_titulo:
            proporcao = len(palavras) / len(palavras_titulo)
            relevancia += proporcao * 2.0

        for indicador in ("kit", "upgrade", "combo", "pc gamer", "computador"):
            if indicador in titulo_normalizado and indicador not in termo_normalizado:
                relevancia -= 2.5

        return relevancia

    def _montar_resumo(
        self,
        chave: str,
        produto: dict[str, Any],
    ) -> ResumoProduto | None:
        registros = produto.get("registros") or []

        precos = [
            float(registro["preco"])
            for registro in registros
            if isinstance(registro, dict)
            and not isinstance(registro.get("preco"), bool)
            and isinstance(registro.get("preco"), (int, float))
        ]

        if not precos:
            return None

        preco_atual = precos[-1]
        menor_preco = min(precos)

        primeiro_registro_em = str(produto.get("primeiro_registro_em") or "")

        return ResumoProduto(
            chave=chave,
            titulo=str(produto.get("titulo") or "Produto sem nome"),
            link=str(produto.get("link") or ""),
            categoria=str(produto.get("categoria") or ""),
            preco_atual=preco_atual,
            menor_preco=menor_preco,
            maior_preco=max(precos),
            preco_medio=mean(precos),
            quantidade_registros=len(precos),
            primeiro_registro_em=primeiro_registro_em,
            esta_no_menor_preco=preco_atual <= menor_preco,
            dias_de_acompanhamento=calcular_dias_desde(primeiro_registro_em),
        )


def normalizar(texto: str) -> str:
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )

    resultado = re.sub(r"[^a-z0-9 ]", " ", sem_acentos.lower())

    return re.sub(r"\s+", " ", resultado).strip()


def canonizar_categoria(categoria: str) -> str:
    normalizada = normalizar(categoria)

    return CATEGORIAS_CANONICAS.get(normalizada, categoria.strip())


def normalizar_busca(texto: str) -> str:
    """Normaliza e expande aliases sem relaxar a busca por palavra inteira."""

    resultado = normalizar(texto)

    for origem, destino in ALIASES_FRASE.items():
        resultado = re.sub(
            r"(?<![a-z0-9])" + re.escape(origem) + r"(?![a-z0-9])",
            destino,
            resultado,
        )

    tokens: list[str] = []

    for token in resultado.split():
        expansao = ALIASES_TOKEN.get(token)

        if expansao is None:
            tokens.append(token)
        else:
            tokens.extend(expansao)

    return " ".join(tokens)


def contem_palavra(texto: str, palavra: str) -> bool:
    """Casa palavra inteira: "5700x" não encontra "5700x3d"."""

    padrao = r"(?<![a-z0-9])" + re.escape(palavra) + r"(?![a-z0-9])"

    return re.search(padrao, texto) is not None


def calcular_dias_desde(data_iso: str) -> int:
    if not data_iso:
        return 0

    try:
        inicio = datetime.fromisoformat(data_iso)

    except ValueError:
        return 0

    if inicio.tzinfo is not None:
        inicio = inicio.replace(tzinfo=None)

    return max((datetime.now() - inicio).days, 0)


def formatar_data(data_iso: str) -> str:
    if not data_iso:
        return "data desconhecida"

    try:
        return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y %H:%M")

    except ValueError:
        return data_iso[:16]


def formatar_moeda(valor: float) -> str:
    """Formata valores no padrão brasileiro: R$ 1.234,56."""

    formatado = f"{valor:,.2f}"
    formatado = formatado.replace(",", "X").replace(".", ",").replace("X", ".")

    return f"R$ {formatado}"


def formatar_resumo(resumo: ResumoProduto) -> str:
    linhas = [f"📦 {resumo.titulo}", ""]

    periodo = descrever_periodo(resumo)

    if resumo.esta_no_menor_preco:
        linhas.append(f"🏆 {formatar_moeda(resumo.preco_atual)} — menor preço {periodo}")
    else:
        diferenca = resumo.preco_atual - resumo.menor_preco

        linhas.append(f"💰 Preço atual: {formatar_moeda(resumo.preco_atual)}")
        linhas.append(
            f"🔻 Menor {periodo}: {formatar_moeda(resumo.menor_preco)} "
            f"({formatar_moeda(diferenca)} abaixo do atual)"
        )

    linhas.append(f"📊 Média {periodo}: {formatar_moeda(resumo.preco_medio)}")
    linhas.append(f"📈 Maior {periodo}: {formatar_moeda(resumo.maior_preco)}")

    if resumo.categoria:
        linhas.append(f"🏷️ Categoria: {resumo.categoria}")

    linhas.append("")
    linhas.append(
        f"👀 {resumo.quantidade_registros} verificações desde "
        f"{formatar_data(resumo.primeiro_registro_em).split()[0]}"
    )

    linhas.append("")
    linhas.append(avaliar_momento(resumo))

    if not resumo.historico_e_confiavel:
        linhas.append("")
        linhas.append(
            "ℹ️ Acompanho este produto há pouco tempo, então o preço "
            "já pode ter sido menor antes de eu começar a monitorar."
        )

    if resumo.link:
        linhas.append("")
        linhas.append(f"🔗 {resumo.link}")

    return "\n".join(linhas)


def descrever_periodo(resumo: ResumoProduto) -> str:
    """Deixa explícito o recorte de tempo que os dados cobrem."""

    dias = resumo.dias_de_acompanhamento

    if dias >= 365:
        return "no último ano"

    if dias >= 60:
        return f"nos últimos {dias // 30} meses"

    if dias >= 30:
        return "no último mês"

    if dias >= 7:
        return f"nos últimos {dias} dias"

    return "desde que comecei a acompanhar"


def formatar_linha_resumida(resumo: ResumoProduto) -> str:
    titulo = resumo.titulo

    if len(titulo) > 52:
        titulo = titulo[:52].rsplit(" ", 1)[0] + "..."

    marcador = "🏆" if resumo.esta_no_menor_preco else "•"

    return f"{marcador} {titulo} — {formatar_moeda(resumo.preco_atual)}"


def avaliar_momento(resumo: ResumoProduto) -> str:
    """Dá uma leitura simples de se o preço atual está bom."""

    if resumo.esta_no_menor_preco:
        if resumo.historico_e_confiavel:
            return "✅ Está no melhor preço do período que acompanho."

        return "🙂 É o menor preço desde que comecei a acompanhar."

    if resumo.preco_atual <= resumo.preco_medio:
        return "🙂 Está abaixo da média registrada."

    diferenca_percentual = ((resumo.preco_atual / resumo.preco_medio) - 1) * 100

    return f"⏳ Está {diferenca_percentual:.0f}% acima da média. Talvez valha esperar."


def extrair_argumento_comando(texto: str) -> str:
    partes = texto.split(maxsplit=1)

    if len(partes) < 2:
        return ""

    return partes[1].strip()


def separar_comparacao(texto: str) -> tuple[str, str] | None:
    """Aceita 'A vs B' ou 'A versus B', exigindo termos dos dois lados."""

    correspondencia = re.match(
        r"^\s*(.+?)\s+(?:vs\.?|versus)\s+(.+?)\s*$",
        texto,
        flags=re.IGNORECASE,
    )

    if correspondencia is None:
        return None

    esquerda = correspondencia.group(1).strip()
    direita = correspondencia.group(2).strip()

    if (
        len(normalizar_busca(esquerda)) < MINIMO_CARACTERES_BUSCA
        or len(normalizar_busca(direita)) < MINIMO_CARACTERES_BUSCA
    ):
        return None

    return esquerda, direita


def formatar_historico(
    resumo: ResumoProduto,
    pontos: list[PontoHistorico],
) -> str:
    linhas = [
        f"📈 HISTÓRICO — {resumo.titulo}",
        "",
        f"Agora: {formatar_moeda(resumo.preco_atual)}",
        f"Menor registrado: {formatar_moeda(resumo.menor_preco)}",
        f"Média: {formatar_moeda(resumo.preco_medio)}",
        "",
        "Últimas verificações com preço registrado:",
    ]

    if not pontos:
        linhas.append("Ainda não há pontos suficientes para listar.")
    else:
        for ponto in reversed(pontos):
            linhas.append(f"• {formatar_data(ponto.coletado_em)} — {formatar_moeda(ponto.preco)}")

    linhas.extend(
        [
            "",
            (
                f"Base: {resumo.quantidade_registros} registros desde "
                f"{formatar_data(resumo.primeiro_registro_em).split()[0]}."
            ),
        ]
    )

    if not resumo.historico_e_confiavel:
        linhas.extend(
            [
                "",
                (
                    "ℹ️ O histórico ainda é curto. Esses valores representam "
                    "somente o período que já monitorei."
                ),
            ]
        )

    return "\n".join(linhas)


def formatar_menor_preco(resumo: ResumoProduto) -> str:
    periodo = descrever_periodo(resumo)

    linhas = [
        f"🏆 MENOR PREÇO — {resumo.titulo}",
        "",
        f"Menor {periodo}: {formatar_moeda(resumo.menor_preco)}",
        f"Preço atual: {formatar_moeda(resumo.preco_atual)}",
    ]

    if resumo.esta_no_menor_preco:
        linhas.append("✅ O preço atual está empatado com o menor que registrei.")
    else:
        diferenca = resumo.preco_atual - resumo.menor_preco
        percentual = (
            ((resumo.preco_atual / resumo.menor_preco) - 1) * 100 if resumo.menor_preco > 0 else 0.0
        )

        linhas.append(
            f"⏳ Hoje está {formatar_moeda(diferenca)} " f"({percentual:.1f}%) acima desse menor."
        )

    linhas.append(
        f"👀 {resumo.quantidade_registros} registros desde "
        f"{formatar_data(resumo.primeiro_registro_em).split()[0]}."
    )

    if not resumo.historico_e_confiavel:
        linhas.extend(
            [
                "",
                (
                    "ℹ️ Ainda acompanho este produto há pouco tempo; "
                    "ele pode ter custado menos antes do meu monitoramento."
                ),
            ]
        )

    if resumo.link:
        linhas.extend(["", f"🔗 {resumo.link}"])

    return "\n".join(linhas)


def formatar_categoria(
    termo: str,
    resultados: list[ResumoProduto],
) -> str:
    linhas = [f"🏷️ CATEGORIA — {termo}", ""]

    for indice, resumo in enumerate(resultados, start=1):
        marcador = "🏆" if resumo.esta_no_menor_preco else "•"
        linhas.append(
            f"{indice}. {marcador} {resumo.titulo} — " f"{formatar_moeda(resumo.preco_atual)}"
        )

    linhas.extend(
        [
            "",
            "🏆 = está no menor preço do período que acompanho.",
            "Mande o nome de um produto para ver os detalhes.",
        ]
    )

    return "\n".join(linhas)


def escolher_representante_comparacao(
    resultados: list[ResumoProduto],
) -> ResumoProduto | None:
    """Escolhe um anúncio representativo e evita outliers grosseiros de preço.

    A busca pode encontrar anúncios corretos, porém absurdamente caros.
    Para comparação, calculamos a mediana dos preços atuais, descartamos
    candidatos muito distantes dela e então priorizamos histórico mais
    robusto e preço atual mais próximo do próprio mínimo.
    """

    if not resultados:
        return None

    precos = sorted(resumo.preco_atual for resumo in resultados if resumo.preco_atual > 0)

    if not precos:
        return resultados[0]

    meio = len(precos) // 2

    if len(precos) % 2:
        mediana = precos[meio]
    else:
        mediana = (precos[meio - 1] + precos[meio]) / 2

    limite_inferior = mediana * 0.55
    limite_superior = mediana * 1.80

    plausiveis = [
        resumo for resumo in resultados if limite_inferior <= resumo.preco_atual <= limite_superior
    ]

    candidatos = plausiveis or resultados

    return max(
        candidatos,
        key=lambda resumo: (
            resumo.quantidade_registros,
            resumo.esta_no_menor_preco,
            -resumo.distancia_do_menor_percentual,
            -abs(resumo.preco_atual - mediana),
        ),
    )


def formatar_comparacao(
    termo_a: str,
    resumo_a: ResumoProduto,
    termo_b: str,
    resumo_b: ResumoProduto,
) -> str:
    linhas = [
        "⚖️ COMPARAÇÃO DE PREÇOS",
        "",
        f"A) {resumo_a.titulo}",
        f"Agora: {formatar_moeda(resumo_a.preco_atual)}",
        f"Menor registrado: {formatar_moeda(resumo_a.menor_preco)}",
        f"Média: {formatar_moeda(resumo_a.preco_medio)}",
        f"Momento: {avaliar_momento(resumo_a)}",
        "",
        f"B) {resumo_b.titulo}",
        f"Agora: {formatar_moeda(resumo_b.preco_atual)}",
        f"Menor registrado: {formatar_moeda(resumo_b.menor_preco)}",
        f"Média: {formatar_moeda(resumo_b.preco_medio)}",
        f"Momento: {avaliar_momento(resumo_b)}",
        "",
    ]

    if resumo_a.preco_atual < resumo_b.preco_atual:
        diferenca = resumo_b.preco_atual - resumo_a.preco_atual
        linhas.append(f"💵 {termo_a} está {formatar_moeda(diferenca)} mais barato agora.")
    elif resumo_b.preco_atual < resumo_a.preco_atual:
        diferenca = resumo_a.preco_atual - resumo_b.preco_atual
        linhas.append(f"💵 {termo_b} está {formatar_moeda(diferenca)} mais barato agora.")
    else:
        linhas.append("💵 Os dois estão com o mesmo preço atual.")

    melhor_relacao = min(
        (resumo_a, "A"),
        (resumo_b, "B"),
        key=lambda item: item[0].distancia_da_media_percentual,
    )

    linhas.append(
        f"📊 O item {melhor_relacao[1]} está em posição melhor "
        "em relação à própria média histórica."
    )
    linhas.append("")
    linhas.append(
        "ℹ️ Isto compara preços e histórico. Não é uma comparação técnica "
        "de desempenho ou qualidade dos produtos."
    )

    return "\n".join(linhas)


async def comando_start(update: Update, contexto: ContextTypes.DEFAULT_TYPE) -> None:
    consulta: ConsultaHistorico = contexto.application.bot_data["consulta"]

    mensagem = (
        "Oi! Eu monitoro preços de hardware, periféricos, eletrônicos "
        "e produtos de setup e guardo o histórico do que encontro.\n\n"
        f"Tenho {consulta.quantidade_produtos()} produtos acompanhados "
        "no momento.\n\n"
        "Você pode simplesmente me mandar o nome de um produto.\n\n"
        "Exemplos:\n"
        "• ryzen 7 5700x\n"
        "• r7 5700x\n"
        "• rtx 4060 vs rx 7600\n\n"
        "Comandos:\n"
        "• /menorpreco ryzen 7 5700x\n"
        "• /historico ryzen 7 5700x\n"
        "• /categoria monitor\n"
        "• /categorias\n"
        "• /ajuda\n\n"
        f"As ofertas eu publico aqui: {LINK_CANAL}"
    )

    if update.message is not None:
        await update.message.reply_text(mensagem)


async def comando_ajuda(update: Update, contexto: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = (
        "🔎 BUSCA\n"
        "Mande o nome do produto normalmente.\n"
        "Ex.: ryzen 7 5700x\n\n"
        "🏆 MENOR PREÇO\n"
        "/menorpreco ryzen 7 5700x\n\n"
        "📈 HISTÓRICO\n"
        "/historico ryzen 7 5700x\n\n"
        "🏷️ CATEGORIA\n"
        "/categoria monitor\n"
        "/categorias\n\n"
        "⚖️ COMPARAÇÃO\n"
        "rtx 4060 vs rx 7600\n\n"
        "A comparação é somente de preço/histórico. "
        "Não compara FPS, desempenho ou qualidade.\n\n"
        "Só consigo responder sobre produtos que já passaram "
        "pelo monitoramento."
    )

    if update.message is not None:
        await update.message.reply_text(mensagem)


async def comando_menor_preco(
    update: Update,
    contexto: ContextTypes.DEFAULT_TYPE,
) -> None:
    mensagem = update.message

    if mensagem is None:
        return

    termo = extrair_argumento_comando(mensagem.text or "")

    if len(normalizar_busca(termo)) < MINIMO_CARACTERES_BUSCA:
        await mensagem.reply_text("Use assim:\n/menorpreco ryzen 7 5700x")
        return

    consulta: ConsultaHistorico = contexto.application.bot_data["consulta"]
    resultados = consulta.buscar(termo, limite=1)

    if not resultados:
        await mensagem.reply_text("Não encontrei esse produto no meu histórico.")
        return

    await mensagem.reply_text(formatar_menor_preco(resultados[0]))


async def comando_historico(
    update: Update,
    contexto: ContextTypes.DEFAULT_TYPE,
) -> None:
    mensagem = update.message

    if mensagem is None:
        return

    termo = extrair_argumento_comando(mensagem.text or "")

    if len(normalizar_busca(termo)) < MINIMO_CARACTERES_BUSCA:
        await mensagem.reply_text("Use assim:\n/historico ryzen 7 5700x")
        return

    consulta: ConsultaHistorico = contexto.application.bot_data["consulta"]
    resultados = consulta.buscar(termo, limite=1)

    if not resultados:
        await mensagem.reply_text("Não encontrei esse produto no meu histórico.")
        return

    resumo = resultados[0]
    pontos = consulta.obter_pontos_historico(resumo.chave)

    await mensagem.reply_text(formatar_historico(resumo, pontos))


async def comando_categoria(
    update: Update,
    contexto: ContextTypes.DEFAULT_TYPE,
) -> None:
    mensagem = update.message

    if mensagem is None:
        return

    termo = extrair_argumento_comando(mensagem.text or "")

    if len(normalizar(termo)) < 2:
        await mensagem.reply_text(
            "Use assim:\n/categoria monitor\n\n" "Para ver os nomes disponíveis, use /categorias."
        )
        return

    consulta: ConsultaHistorico = contexto.application.bot_data["consulta"]
    resultados = consulta.buscar_por_categoria(termo)

    if not resultados:
        await mensagem.reply_text(
            "Não encontrei essa categoria no histórico.\n\n"
            "Use /categorias para ver as categorias disponíveis."
        )
        return

    await mensagem.reply_text(formatar_categoria(termo, resultados))


async def comando_categorias(
    update: Update,
    contexto: ContextTypes.DEFAULT_TYPE,
) -> None:
    mensagem = update.message

    if mensagem is None:
        return

    consulta: ConsultaHistorico = contexto.application.bot_data["consulta"]
    categorias = consulta.listar_categorias()

    if not categorias:
        await mensagem.reply_text("Ainda não tenho categorias registradas no histórico.")
        return

    linhas = ["🏷️ CATEGORIAS MONITORADAS", ""]

    for categoria, quantidade in categorias:
        linhas.append(f"• {categoria} — {quantidade} produto(s)")

    linhas.extend(
        [
            "",
            "Consulte uma delas com:",
            "/categoria nome da categoria",
        ]
    )

    await mensagem.reply_text("\n".join(linhas))


async def responder_comparacao(
    mensagem: Any,
    consulta: ConsultaHistorico,
    termo_a: str,
    termo_b: str,
) -> None:
    # Busca vários anúncios para evitar que um único anúncio absurdamente
    # caro vire o representante do modelo inteiro na comparação.
    resultados_a = consulta.buscar(termo_a, limite=20)
    resultados_b = consulta.buscar(termo_b, limite=20)

    resumo_a = escolher_representante_comparacao(resultados_a)
    resumo_b = escolher_representante_comparacao(resultados_b)

    faltando: list[str] = []

    if resumo_a is None:
        faltando.append(termo_a)

    if resumo_b is None:
        faltando.append(termo_b)

    if faltando:
        await mensagem.reply_text(
            "Não consegui comparar porque não encontrei no histórico: " + ", ".join(faltando) + "."
        )
        return

    await mensagem.reply_text(
        formatar_comparacao(
            termo_a=termo_a,
            resumo_a=resumo_a,
            termo_b=termo_b,
            resumo_b=resumo_b,
        )
    )


async def responder_consulta(update: Update, contexto: ContextTypes.DEFAULT_TYPE) -> None:
    mensagem = update.message

    if mensagem is None:
        # Publicações de canal e edições não têm "message".
        return

    texto = (mensagem.text or "").strip()

    if not texto:
        return

    consulta: ConsultaHistorico = contexto.application.bot_data["consulta"]

    comparacao = separar_comparacao(texto)

    if comparacao is not None:
        termo_a, termo_b = comparacao

        await responder_comparacao(
            mensagem=mensagem,
            consulta=consulta,
            termo_a=termo_a,
            termo_b=termo_b,
        )
        return

    if len(normalizar_busca(texto)) < MINIMO_CARACTERES_BUSCA:
        await mensagem.reply_text(
            "Escreve um pouco mais do nome do produto para eu conseguir buscar."
        )
        return

    resultados = consulta.buscar(texto)

    if not resultados:
        await mensagem.reply_text(
            "Ainda não tenho esse produto no histórico.\n\n"
            "Pode ser que ele não tenha aparecido nas minhas buscas "
            "ou que o nome esteja diferente. Tenta com menos palavras, "
            "só a marca e o modelo.\n\n"
            f"As ofertas que encontro vão para {LINK_CANAL}"
        )
        return

    if len(resultados) == 1:
        await mensagem.reply_text(formatar_resumo(resultados[0]))
        return

    partes = [formatar_resumo(resultados[0])]

    outros = resultados[1:]

    if outros:
        partes.append("")
        partes.append("—" * 18)
        partes.append("")
        partes.append("Também encontrei:")
        partes.append("")

        for resumo in outros:
            partes.append(formatar_linha_resumida(resumo))

        partes.append("")
        partes.append("Manda o nome mais completo para ver os detalhes de um deles.")

    await mensagem.reply_text("\n".join(partes))


async def tratar_erro(update: object, contexto: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Erro ao processar atualização.", exc_info=contexto.error)


def main() -> None:
    configuracoes = Configuracoes()

    consulta = ConsultaHistorico()

    logger.info(
        "Bot de consulta iniciando com %s produto(s) no histórico.",
        consulta.quantidade_produtos(),
    )

    aplicacao = Application.builder().token(configuracoes.telegram_bot_token).build()

    aplicacao.bot_data["consulta"] = consulta

    aplicacao.add_handler(CommandHandler("start", comando_start, filters.ChatType.PRIVATE))
    aplicacao.add_handler(CommandHandler("ajuda", comando_ajuda, filters.ChatType.PRIVATE))
    aplicacao.add_handler(CommandHandler("help", comando_ajuda, filters.ChatType.PRIVATE))
    aplicacao.add_handler(
        CommandHandler("menorpreco", comando_menor_preco, filters.ChatType.PRIVATE)
    )
    aplicacao.add_handler(CommandHandler("historico", comando_historico, filters.ChatType.PRIVATE))
    aplicacao.add_handler(CommandHandler("categoria", comando_categoria, filters.ChatType.PRIVATE))
    aplicacao.add_handler(
        CommandHandler("categorias", comando_categorias, filters.ChatType.PRIVATE)
    )

    # ChatType.PRIVATE evita que o bot reaja às publicações do canal.
    aplicacao.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
            responder_consulta,
        )
    )

    aplicacao.add_error_handler(tratar_erro)

    logger.info("Bot de consulta pronto. Aguardando mensagens no privado.")

    aplicacao.run_polling()


if __name__ == "__main__":
    main()
