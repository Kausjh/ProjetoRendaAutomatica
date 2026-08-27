# 63.8738, -149.7525

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import random
import re
import unicodedata
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol

from models.oferta import Oferta
from repositories.radar_editorial_repository import RadarEditorialRepository
from services.analisador_contexto_editorial import (
    AnalisadorContextoEditorial,
    SinalContextoEditorial,
)
from services.historico_precos_service import ResultadoHistoricoPreco

logger = logging.getLogger(__name__)


class BotEditorial(Protocol):
    async def responder_mensagem(
        self,
        mensagem_id: int,
        mensagem: str,
    ) -> None: ...

    async def enviar_mensagem(
        self,
        mensagem: str,
    ) -> None: ...

    async def enviar_enquete(
        self,
        pergunta: str,
        opcoes: Sequence[str],
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class IntervencaoEditorial:
    persona: str
    motivo: str
    texto: str


@dataclass(frozen=True, slots=True)
class InteracaoProgramada:
    tipo: str
    minuto_do_dia: int
    texto: str
    opcoes: tuple[str, ...] = ()


class RadarEditorial:
    """Camada editorial humana sem transformar o canal em outro tipo de spam."""

    COMENTARIOS_MAXIMOS_DIA = 8
    INTERVALO_MINIMO_COMENTARIOS = timedelta(minutes=12)
    ATRASO_RESPOSTA_MINIMO_SEGUNDOS = 8
    ATRASO_RESPOSTA_MAXIMO_SEGUNDOS = 38
    CHANCE_BASE = 0.10
    PONTUACAO_MINIMA_COMENTARIO_GENERICO = 76.0
    PONTUACAO_MINIMA_CONTEXTO_LEVE = 72.0
    LIMITE_REPETICAO_TEXTOS = 40

    def __init__(
        self,
        repository: RadarEditorialRepository | None = None,
        rng: random.Random | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.repository = repository or RadarEditorialRepository()
        self.analisador_contexto = AnalisadorContextoEditorial()
        self.rng = rng or random.Random()
        self.sleeper = sleeper
        self.ativo = self._env_booleano("RADAR_EDITORIAL_ATIVO", True)
        self.interacao_manha_ativa = self._env_booleano(
            "RADAR_EDITORIAL_INTERACAO_MANHA",
            True,
        )
        self._proxima_tentativa_interacao_em: datetime | None = None

    @staticmethod
    def _env_booleano(nome: str, padrao: bool) -> bool:
        valor = os.getenv(nome)
        if valor is None:
            return padrao

        return valor.strip().casefold() not in {
            "0",
            "false",
            "nao",
            "não",
            "off",
        }

    @staticmethod
    def _normalizar(texto: str) -> str:
        decomposed = unicodedata.normalize("NFKD", texto)
        sem_acentos = "".join(
            caractere for caractere in decomposed if not unicodedata.combining(caractere)
        )
        return re.sub(r"\s+", " ", sem_acentos.casefold()).strip()

    @staticmethod
    def _assinatura(texto: str) -> str:
        normalizado = RadarEditorial._normalizar(texto)
        return normalizado[:42]

    @staticmethod
    def _queda_percentual(
        resultado_historico: ResultadoHistoricoPreco | None,
    ) -> float:
        if resultado_historico is None or not resultado_historico.preco_caiu:
            return 0.0

        return abs(float(resultado_historico.variacao_percentual))

    def _bloqueado_por_frequencia(self, agora: datetime) -> bool:
        if self.repository.comentarios_no_dia(agora.date()) >= (self.COMENTARIOS_MAXIMOS_DIA):
            return True

        ultima = self.repository.ultima_intervencao_em()
        if ultima is None:
            return False

        if ultima.tzinfo is None and agora.tzinfo is not None:
            ultima = ultima.replace(tzinfo=agora.tzinfo)

        return agora - ultima < self.INTERVALO_MINIMO_COMENTARIOS

    def _escolher_sem_repetir(
        self,
        candidatos: list[tuple[str, str]],
    ) -> tuple[str, str]:
        ultima_persona = self.repository.ultima_persona()
        textos_recentes = self.repository.textos_recentes(self.LIMITE_REPETICAO_TEXTOS)
        assinaturas_recentes = {self._assinatura(texto) for texto in textos_recentes}

        filtrados = [
            item for item in candidatos if self._assinatura(item[1]) not in assinaturas_recentes
        ]

        if not filtrados:
            filtrados = list(candidatos)

        sem_persona_repetida = [item for item in filtrados if item[0] != ultima_persona]

        if sem_persona_repetida:
            filtrados = sem_persona_repetida

        return self.rng.choice(filtrados)

    @staticmethod
    def _candidatos_contexto_tecnico(
        sinal: SinalContextoEditorial,
    ) -> list[tuple[str, str]]:
        referencia = sinal.referencia

        if sinal.tipo == "incompatibilidade_socket":
            return [
                (
                    "tecnico",
                    f"{referencia}: essa combinação de plataforma não fecha. eu conferiria o anúncio antes de comprar",
                ),
                (
                    "fiscal",
                    f"{referencia} no mesmo anúncio. ou o título misturou peças diferentes, ou tem compatibilidade errada aí",
                ),
                (
                    "estagiario",
                    f"{referencia}. eu parei nessa parte porque socket não costuma aceitar negociação",
                ),
            ]

        if sinal.tipo == "incompatibilidade_memoria":
            return [
                (
                    "tecnico",
                    f"{referencia}: a combinação de CPU e memória não bate tecnicamente. confere a ficha antes de fechar",
                ),
                (
                    "fiscal",
                    f"{referencia} apareceu junto. isso merece revisão porque as plataformas não combinam",
                ),
                (
                    "estagiario",
                    f"{referencia}. dessa vez eu não culpo o algoritmo; a ficha técnica que tá brigando consigo mesma",
                ),
            ]

        if sinal.tipo == "marketing_cpu_basica":
            return [
                (
                    "estagiario",
                    f"{referencia} com 'gamer' no anúncio. o marketing chegou antes do benchmark",
                ),
                (
                    "fiscal",
                    f"{referencia} numa máquina vendida como gamer. eu julgaria pelo hardware, não pelo adjetivo",
                ),
                (
                    "tecnico",
                    f"{referencia} é uma CPU bem básica pra proposta gamer. vale conferir o uso real antes de comprar",
                ),
            ]

        if sinal.tipo == "upgrade_antigo":
            return [
                (
                    "estagiario",
                    f"rapaziada, eu vi o {referencia} também. o “upgrade” foi decisão de outro setor",
                ),
                (
                    "fiscal",
                    f"{referencia} num anúncio chamado upgrade. a palavra tá trabalhando bastante hoje",
                ),
                (
                    "tecnico",
                    f"{referencia}: pra recuperar máquina antiga, beleza. pra montar do zero, eu olharia plataforma mais nova",
                ),
            ]

        if sinal.tipo == "marketing_gpu_desproporcional":
            return [
                (
                    "estagiario",
                    f"{referencia} e promessa grande no mesmo anúncio. o marketing acordou confiante",
                ),
                (
                    "fiscal",
                    f"{referencia} com esse papo de 4K/ultra. eu leria o título com uma sobrancelha levantada",
                ),
                (
                    "tecnico",
                    f"{referencia} é uma placa bem modesta hoje. não deixa “4K” ou “ultra” no título fazer benchmark por você",
                ),
            ]

        if sinal.tipo == "gpu_antiga_entrada":
            return [
                (
                    "estagiario",
                    f"{referencia} apareceu. não é crime ser velha; o preço só precisa respeitar a idade",
                ),
                (
                    "fiscal",
                    f"{referencia} em pleno expediente. se o preço não estiver humilde também, eu protesto",
                ),
                (
                    "tecnico",
                    f"{referencia} ainda pode resolver uso básico ou PC antigo. só não trata como placa atual",
                ),
            ]

        if sinal.tipo == "cpu_antiga":
            geracao = int(sinal.valor) if sinal.valor is not None and sinal.valor < 100 else None
            descricao = f"{geracao}ª geração" if geracao is not None else referencia
            return [
                (
                    "estagiario",
                    f"{descricao} apareceu por aqui. respeito aos mais velhos, mas o preço precisa colaborar com a nostalgia",
                ),
                (
                    "fiscal",
                    f"tem {referencia} aqui. pode servir, mas o nome da linha não apaga a idade do chip",
                ),
                (
                    "tecnico",
                    f"{referencia} ainda pode fazer sentido em máquina antiga. pra projeto novo, eu compararia com plataforma mais recente",
                ),
            ]

        if sinal.tipo == "xeon_antigo":
            return [
                (
                    "estagiario",
                    f"{referencia}. o clássico “muito núcleo, pouca juventude” voltou pra fila",
                ),
                (
                    "fiscal",
                    f"{referencia} pode ser barato, mas vem junto com uma plataforma velha. compra sabendo o pacote inteiro",
                ),
                (
                    "tecnico",
                    f"{referencia}: dá pra extrair valor em projeto barato, mas eficiência e plataforma já entregam a idade",
                ),
            ]

        if sinal.tipo == "ram_baixa":
            return [
                (
                    "estagiario",
                    f"{referencia}. dá pra abrir o sistema. a negociação com as abas do navegador fica pra depois",
                ),
                (
                    "fiscal",
                    f"{referencia} hoje é bem apertado. eu já colocaria expansão na conta antes de chamar de oferta",
                ),
                (
                    "tecnico",
                    f"{referencia}: serve pra uso leve, mas multitarefa vai sentir rápido",
                ),
            ]

        if sinal.tipo == "armazenamento_apertado":
            return [
                (
                    "estagiario",
                    f"{referencia}. rápido pra instalar e rápido pra ficar sem espaço",
                ),
                (
                    "fiscal",
                    f"{referencia} é capacidade de sobrevivência. se for upgrade principal, eu faria as contas de espaço antes",
                ),
                (
                    "tecnico",
                    f"{referencia}: ainda serve pra sistema leve, mas como armazenamento principal fica apertado bem rápido",
                ),
            ]

        if sinal.tipo == "ddr3":
            return [
                (
                    "estagiario",
                    "DDR3 na ficha. não é proibido, só veio de uma época em que eu provavelmente ainda não trabalhava aqui",
                ),
                (
                    "fiscal",
                    "DDR3 apareceu. pra manutenção de máquina antiga, ok. pra montar do zero, eu questionaria",
                ),
                (
                    "tecnico",
                    "DDR3 normalmente significa plataforma antiga. faz sentido em reaproveitamento; em projeto novo, compara antes",
                ),
            ]

        if sinal.tipo == "monitor_gamer_basico":
            hz = int(sinal.valor or 0)
            return [
                (
                    "estagiario",
                    f"{hz} Hz e “gamer” no título. o adjetivo tá trabalhando mais que a taxa de atualização",
                ),
                (
                    "fiscal",
                    f"monitor gamer de {hz} Hz. pode ser um monitor ok; o “gamer” é que precisa baixar o tom",
                ),
                (
                    "tecnico",
                    f"{hz} Hz é básico hoje pra proposta gamer. eu olharia painel e preço antes do rótulo",
                ),
            ]

        return [
            (
                "fiscal",
                f"{referencia} chamou atenção aqui. vale olhar o contexto antes de comprar só pelo título",
            ),
            (
                "estagiario",
                f"{referencia}. eu só tô dizendo que essa parte do anúncio merece uma segunda olhada",
            ),
        ]

    def _candidatos_republicacao_queda(
        self,
        queda: float,
    ) -> list[tuple[str, str]]:
        return [
            (
                "cacador",
                (
                    f"esse vocês já viram. voltou porque caiu cerca de {queda:.0f}%. "
                    "aí eu deixo repetir sem reclamar"
                ),
            ),
            (
                "estagiario",
                (
                    f"sim, é repetido. mas voltou uns {queda:.0f}% mais barato, "
                    "então dessa vez eu tenho defesa"
                ),
            ),
            (
                "fiscal",
                (
                    f"repetição autorizada: caiu aproximadamente {queda:.0f}% "
                    "desde a referência anterior"
                ),
            ),
            (
                "tecnico",
                (
                    f"esse voltou com preço melhor: cerca de {queda:.0f}% abaixo "
                    "da referência anterior. agora a comparação mudou"
                ),
            ),
            (
                "estagiario",
                (
                    f"desarquivaram esse porque caiu mais ou menos {queda:.0f}%. "
                    "eu também preferia não repetir sem motivo"
                ),
            ),
        ]

    def _candidatos_queda_forte(
        self,
        queda: float,
    ) -> list[tuple[str, str]]:
        return [
            (
                "cacador",
                (
                    f"{queda:.0f}% pra baixo desde a referência anterior. "
                    "aí sim mudou alguma coisa"
                ),
            ),
            (
                "estagiario",
                (f"caiu uns {queda:.0f}%. até eu parei a planilha pra olhar"),
            ),
            (
                "fiscal",
                (
                    f"queda de aproximadamente {queda:.0f}%. "
                    "agora existe motivo real pra chamar atenção"
                ),
            ),
            (
                "tecnico",
                (
                    f"queda de cerca de {queda:.0f}%. isso já muda bastante "
                    "a comparação com o preço anterior"
                ),
            ),
        ]

    @staticmethod
    def _candidatos_menor_preco() -> list[tuple[str, str]]:
        return [
            (
                "tecnico",
                ("menor preço que a gente já registrou pra esse. " "sem asterisco de marketing"),
            ),
            (
                "cacador",
                (
                    "bateu o menor preço do nosso histórico. "
                    "esse eu achei justo interromper o expediente pra apontar"
                ),
            ),
            (
                "fiscal",
                (
                    "é o menor valor que a gente já registrou aqui. "
                    "não obriga ninguém a comprar, mas a informação é boa"
                ),
            ),
            (
                "estagiario",
                (
                    "menor preço do nosso histórico. "
                    "finalmente a planilha trouxe uma notícia que presta"
                ),
            ),
        ]

    @staticmethod
    def _candidatos_score_alto(score: float) -> list[tuple[str, str]]:
        return [
            (
                "tecnico",
                f"{score:.0f} de score aqui dentro. passou bem acima da régua",
            ),
            (
                "cacador",
                f"nota {score:.0f}. o sistema gostou bastante dessa",
            ),
            (
                "estagiario",
                (f"{score:.0f} de score. o algoritmo gostou. " "eu vou fingir que confio nele"),
            ),
            (
                "fiscal",
                (
                    f"passou com {score:.0f}. raro momento em que o algoritmo "
                    "e a fiscalização não estão brigando"
                ),
            ),
        ]

    @classmethod
    def _candidatos_categoria(
        cls,
        oferta: Oferta,
    ) -> list[tuple[str, str]]:
        categoria = cls._normalizar(str(getattr(oferta, "categoria", "") or ""))
        marca = str(getattr(oferta, "marca", "") or "").strip()

        if "armazenamento" in categoria and not marca:
            return [
                (
                    "tecnico",
                    (
                        "preço chamou atenção. a marca não ajudou muito. "
                        "eu conferiria garantia e especificações antes de colocar no PC principal"
                    ),
                ),
                (
                    "fiscal",
                    (
                        "armazenamento sem muita grife na ficha. pode valer, "
                        "mas eu não compraria só pelo preço"
                    ),
                ),
            ]

        if "memoria" in categoria or "ram" in categoria:
            return [
                (
                    "estagiario",
                    ("mais RAM. pra quem abre 47 abas e chama isso de fluxo de trabalho, " "tá aí"),
                ),
                (
                    "tecnico",
                    (
                        "memória na fila. confere geração, frequência e compatibilidade "
                        "antes de deixar o preço decidir sozinho"
                    ),
                ),
                (
                    "fiscal",
                    (
                        "RAM barata é bonita até chegar a hora de descobrir "
                        "que não conversa direito com o resto da máquina"
                    ),
                ),
            ]

        if "monitor" in categoria:
            return [
                (
                    "estagiario",
                    "monitor de novo. prometo que não recebo comissão por polegada",
                ),
                (
                    "tecnico",
                    (
                        "monitor na pauta. Hz chama atenção, mas painel e tempo de resposta "
                        "continuam existindo"
                    ),
                ),
            ]

        if "processador" in categoria:
            return [
                (
                    "tecnico",
                    (
                        "antes de animar: confere socket e placa-mãe. "
                        "preço bom não faz CPU encaixar no lugar errado"
                    ),
                ),
                (
                    "estagiario",
                    (
                        "CPU na mesa. se alguém comprar socket incompatível, "
                        "eu já deixo registrado que fui contra"
                    ),
                ),
                (
                    "fiscal",
                    (
                        "processador apareceu. geração, plataforma e preço das alternativas "
                        "antes do impulso"
                    ),
                ),
            ]

        if "placa de video" in categoria or "gpu" in categoria:
            return [
                (
                    "fiscal",
                    (
                        "GPU na mesa. confere VRAM, fonte e o preço da concorrência "
                        "antes de jurar amor"
                    ),
                ),
                (
                    "cacador",
                    (
                        "placa de vídeo encontrada. agora começa a tradição de abrir "
                        "cinco comparativos antes de decidir"
                    ),
                ),
                (
                    "tecnico",
                    (
                        "GPU passou pela fila. olha VRAM e consumo junto com o preço; "
                        "o nome da placa não conta a história inteira"
                    ),
                ),
            ]

        return [
            (
                "estagiario",
                (
                    "eu ia postar isso quieto, mas me promoveram pra pessoa "
                    "que comenta as próprias postagens"
                ),
            ),
            (
                "fiscal",
                (
                    "entrou pela combinação de preço e nota. vale olhar; "
                    "não precisa transformar isso em compra por impulso"
                ),
            ),
            (
                "cacador",
                "apareceu na triagem e passou. fica aí pra quem tava procurando",
            ),
        ]

    def avaliar_oferta(
        self,
        *,
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None,
        pontuacao: float,
        deve_republicar_por_queda: bool,
        agora: datetime | None = None,
    ) -> IntervencaoEditorial | None:
        if not self.ativo:
            return None

        momento = agora or datetime.now().astimezone()

        if self._bloqueado_por_frequencia(momento):
            return None

        contexto = self.analisador_contexto.analisar(oferta)
        sinal_contexto = contexto.principal
        queda = self._queda_percentual(resultado_historico)

        motivo: str
        chance: float
        candidatos: list[tuple[str, str]]

        if sinal_contexto is not None and sinal_contexto.severidade >= 4:
            motivo = f"contexto_{sinal_contexto.tipo}"
            chance = 0.96 if sinal_contexto.severidade >= 5 else 0.88
            candidatos = self._candidatos_contexto_tecnico(sinal_contexto)

        elif sinal_contexto is not None and sinal_contexto.severidade >= 3:
            motivo = f"contexto_{sinal_contexto.tipo}"
            chance = 0.62
            candidatos = self._candidatos_contexto_tecnico(sinal_contexto)

        elif deve_republicar_por_queda and queda >= 5:
            motivo = "republicacao_por_queda"
            chance = 0.72
            candidatos = self._candidatos_republicacao_queda(queda)

        elif queda >= 15:
            motivo = "queda_forte"
            chance = 0.52
            candidatos = self._candidatos_queda_forte(queda)

        elif (
            resultado_historico is not None
            and not resultado_historico.primeiro_registro
            and resultado_historico.menor_preco_historico
        ):
            motivo = "menor_preco_historico"
            chance = 0.42
            candidatos = self._candidatos_menor_preco()

        elif pontuacao >= 82:
            motivo = "score_alto"
            chance = 0.30
            candidatos = self._candidatos_score_alto(pontuacao)

        elif sinal_contexto is not None and sinal_contexto.severidade >= 2:
            if pontuacao < self.PONTUACAO_MINIMA_CONTEXTO_LEVE:
                return None
            motivo = f"contexto_{sinal_contexto.tipo}"
            chance = 0.32
            candidatos = self._candidatos_contexto_tecnico(sinal_contexto)

        else:
            if pontuacao < self.PONTUACAO_MINIMA_COMENTARIO_GENERICO:
                return None
            motivo = "comentario_contextual"
            chance = self.CHANCE_BASE
            candidatos = self._candidatos_categoria(oferta)

        if self.rng.random() > chance:
            return None

        persona, texto = self._escolher_sem_repetir(candidatos)

        return IntervencaoEditorial(
            persona=persona,
            motivo=motivo,
            texto=texto,
        )

    async def tentar_comentar_oferta(
        self,
        *,
        bot: BotEditorial,
        mensagem_id: int | None,
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None,
        pontuacao: float,
        deve_republicar_por_queda: bool,
        forcar: bool = False,
    ) -> bool:
        if forcar or mensagem_id is None:
            return False

        agora = datetime.now().astimezone()
        intervencao = self.avaliar_oferta(
            oferta=oferta,
            resultado_historico=resultado_historico,
            pontuacao=pontuacao,
            deve_republicar_por_queda=deve_republicar_por_queda,
            agora=agora,
        )

        if intervencao is None:
            return False

        atraso = self.rng.randint(
            self.ATRASO_RESPOSTA_MINIMO_SEGUNDOS,
            self.ATRASO_RESPOSTA_MAXIMO_SEGUNDOS,
        )
        await self.sleeper(float(atraso))

        try:
            await bot.responder_mensagem(
                mensagem_id,
                intervencao.texto,
            )
        except Exception as erro:
            logger.warning(
                "Radar Editorial não conseguiu comentar a publicação; "
                "a oferta principal permanece publicada. Detalhes: %s",
                erro,
            )
            return False

        enviado_em = datetime.now().astimezone()
        self.repository.registrar_intervencao(
            persona=intervencao.persona,
            motivo=intervencao.motivo,
            texto=intervencao.texto,
            momento=enviado_em,
        )

        logger.info(
            "Radar Editorial: %s comentou uma publicação (%s).",
            intervencao.persona,
            intervencao.motivo,
        )
        return True

    @staticmethod
    def _semente(texto: str) -> int:
        digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)

    def planejar_interacao(
        self,
        data_referencia: date,
    ) -> InteracaoProgramada | None:
        segunda = data_referencia - timedelta(days=data_referencia.weekday())
        rng_semana = random.Random(self._semente(f"radar-editorial-semana:{segunda.isoformat()}"))
        dias_ativos = sorted(rng_semana.sample(range(7), 4))

        if data_referencia.weekday() not in dias_ativos:
            return None

        posicao_no_turno = dias_ativos.index(data_referencia.weekday())

        rng_dia = random.Random(self._semente(f"radar-editorial-dia:{data_referencia.isoformat()}"))
        minuto = rng_dia.randint(
            8 * 60 + 10,
            10 * 60 + 20,
        )

        interacoes: list[tuple[str, str, tuple[str, ...]]] = [
            (
                "enquete",
                (
                    "bom dia. preciso de uma prioridade antes que inventem outra reunião. "
                    "o que eu vigio hoje?"
                ),
                (
                    "Placa de vídeo",
                    "Processador",
                    "SSD / RAM",
                    "Periféricos",
                ),
            ),
            (
                "enquete",
                "qual peça do setup de vocês tá pedindo socorro primeiro?",
                (
                    "GPU",
                    "CPU",
                    "RAM / SSD",
                    "Monitor / periféricos",
                ),
            ),
            (
                "enquete",
                "se eu gastar meu turno inteiro em uma categoria, qual vocês escolhem?",
                (
                    "Placa de vídeo",
                    "Kit upgrade",
                    "Armazenamento",
                    "Monitor",
                ),
            ),
            (
                "enquete",
                (
                    "o técnico quer CPU. o estagiário quer GPU porque dá mais reação. "
                    "decidam por nós"
                ),
                (
                    "Processador",
                    "Placa de vídeo",
                    "Memória",
                    "Periféricos",
                ),
            ),
            (
                "reacao",
                (
                    "deixa um 🔥 se hoje é dia de eu ficar em cima de placa de vídeo. "
                    "se der silêncio eu volto pra planilha"
                ),
                (),
            ),
            (
                "reacao",
                (
                    "reage com 👀 se vocês querem que eu fique caçando queda de preço "
                    "e item estranho hoje"
                ),
                (),
            ),
            (
                "reacao",
                (
                    "⚡ aqui se vocês querem que eu reposte coisa que voltou mais barata. "
                    "prometo não ressuscitar qualquer coisa"
                ),
                (),
            ),
        ]

        rng_semana.shuffle(interacoes)
        tipo, texto, opcoes = interacoes[posicao_no_turno]

        return InteracaoProgramada(
            tipo=tipo,
            minuto_do_dia=minuto,
            texto=texto,
            opcoes=opcoes,
        )

    async def tentar_interacao_do_dia(
        self,
        bot: BotEditorial,
        agora: datetime | None = None,
    ) -> bool:
        if not self.ativo or not self.interacao_manha_ativa:
            return False

        momento = agora or datetime.now().astimezone()

        if self.repository.interacao_diaria_enviada(momento.date()):
            return False

        if (
            self._proxima_tentativa_interacao_em is not None
            and momento < self._proxima_tentativa_interacao_em
        ):
            return False

        plano = self.planejar_interacao(momento.date())
        if plano is None:
            return False

        minuto_atual = momento.hour * 60 + momento.minute
        if minuto_atual < plano.minuto_do_dia:
            return False

        if minuto_atual > 11 * 60 + 30:
            return False

        try:
            if plano.tipo == "enquete":
                await bot.enviar_enquete(
                    plano.texto,
                    plano.opcoes,
                )
            else:
                await bot.enviar_mensagem(plano.texto)
        except Exception as erro:
            self._proxima_tentativa_interacao_em = momento + timedelta(minutes=15)
            logger.warning(
                "Radar Editorial adiou a interação de abertura após falha no Telegram. "
                "Detalhes: %s",
                erro,
            )
            return False

        self.repository.registrar_interacao_diaria(
            data_referencia=momento.date(),
            tipo=plano.tipo,
            momento=momento,
        )
        self._proxima_tentativa_interacao_em = None

        logger.info(
            "Radar Editorial: interação de abertura enviada (%s).",
            plano.tipo,
        )
        return True
