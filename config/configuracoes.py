# 63.8738, -149.7525

import os
import re

from dotenv import load_dotenv


class Configuracoes:

    def __init__(self) -> None:
        load_dotenv()

        self.telegram_bot_token = self._buscar_variavel_obrigatoria("TELEGRAM_BOT_TOKEN")

        self.channel_id = self._buscar_variavel_obrigatoria("CHANNEL_ID")

        self.identificador_marca = (
            self._buscar_variavel_obrigatoria("IDENTIFICADOR_MARCA").strip().lower()
        )

        self.limite_ofertas = self._buscar_inteiro(nome="LIMITE_OFERTAS", valor_padrao=20)

        self.maximo_publicacoes = self._buscar_inteiro(nome="MAXIMO_PUBLICACOES", valor_padrao=5)

        self.intervalo_publicacoes = self._buscar_decimal(
            nome="INTERVALO_PUBLICACOES", valor_padrao=2.0
        )

        self.desconto_minimo = self._buscar_decimal(nome="DESCONTO_MINIMO", valor_padrao=0)

        self.preco_maximo = self._buscar_decimal(nome="PRECO_MAXIMO", valor_padrao=40)

        self.restricao_madrugada_ativa = self._buscar_booleano(
            nome="RESTRICAO_MADRUGADA_ATIVA", valor_padrao=True
        )

        self.hora_inicio_madrugada = self._buscar_inteiro(
            nome="HORA_INICIO_MADRUGADA", valor_padrao=23
        )

        self.hora_fim_madrugada = self._buscar_inteiro(nome="HORA_FIM_MADRUGADA", valor_padrao=8)

        self.queda_minima_madrugada = self._buscar_decimal(
            nome="QUEDA_MINIMA_MADRUGADA", valor_padrao=25.0
        )

        self.pontuacao_minima_madrugada = self._buscar_decimal(
            nome="PONTUACAO_MINIMA_MADRUGADA", valor_padrao=90.0
        )

        self.registros_minimos_madrugada = self._buscar_inteiro(
            nome="REGISTROS_MINIMOS_MADRUGADA", valor_padrao=3
        )

        self.nota_comprador_minima_madrugada = self._buscar_decimal(
            nome="NOTA_COMPRADOR_MINIMA_MADRUGADA", valor_padrao=60.0
        )

        self.queda_minima_menor_preco_madrugada = self._buscar_decimal(
            nome="QUEDA_MINIMA_MENOR_PRECO_MADRUGADA", valor_padrao=15.0
        )

        self.queda_maxima_automatica_madrugada = self._buscar_decimal(
            nome="QUEDA_MAXIMA_AUTOMATICA_MADRUGADA", valor_padrao=55.0
        )

        self.detector_anomalia_ativo = self._buscar_booleano(
            nome="DETECTOR_ANOMALIA_ATIVO", valor_padrao=True
        )

        self.queda_minima_anomalia = self._buscar_decimal(
            nome="QUEDA_MINIMA_ANOMALIA", valor_padrao=45.0
        )

        self.queda_minima_preco_bugado = self._buscar_decimal(
            nome="QUEDA_MINIMA_PRECO_BUGADO", valor_padrao=55.0
        )

        self.queda_maxima_anomalia_publicavel = self._buscar_decimal(
            nome="QUEDA_MAXIMA_ANOMALIA_PUBLICAVEL", valor_padrao=75.0
        )

        self.registros_minimos_anomalia = self._buscar_inteiro(
            nome="REGISTROS_MINIMOS_ANOMALIA", valor_padrao=4
        )

        self.confianca_minima_anomalia = self._buscar_decimal(
            nome="CONFIANCA_MINIMA_ANOMALIA", valor_padrao=75.0
        )

        self.curadoria_publicacao_ativa = self._buscar_booleano(
            nome="CURADORIA_PUBLICACAO_ATIVA", valor_padrao=True
        )

        self.nota_minima_curadoria = self._buscar_decimal(
            nome="NOTA_MINIMA_CURADORIA", valor_padrao=55.0
        )

        self.deduplicacao_canonica_ativa = self._buscar_booleano(
            nome="DEDUPLICACAO_CANONICA_ATIVA", valor_padrao=True
        )

        self.confianca_minima_deduplicacao = self._buscar_decimal(
            nome="CONFIANCA_MINIMA_DEDUPLICACAO", valor_padrao=90.0
        )

        # Fila inteligente / publicação contínua
        self.pontuacao_minima_fila = self._buscar_decimal(
            nome="PONTUACAO_MINIMA_FILA", valor_padrao=72.0
        )

        self.fila_reposicao_adaptativa_ativa = self._buscar_booleano(
            nome="FILA_REPOSICAO_ADAPTATIVA_ATIVA", valor_padrao=True
        )

        self.pontuacao_minima_reposicao_fila = self._buscar_decimal(
            nome="PONTUACAO_MINIMA_REPOSICAO_FILA", valor_padrao=45.0
        )

        self.alvo_minimo_pendentes_fila = self._buscar_inteiro(
            nome="ALVO_MINIMO_PENDENTES_FILA", valor_padrao=2
        )

        self.maximo_entradas_fila_por_ciclo = self._buscar_inteiro(
            nome="MAXIMO_ENTRADAS_FILA_POR_CICLO", valor_padrao=12
        )

        self.tamanho_maximo_fila = self._buscar_inteiro(nome="TAMANHO_MAXIMO_FILA", valor_padrao=30)

        self.fila_idade_maxima_minutos = self._buscar_decimal(
            nome="FILA_IDADE_MAXIMA_MINUTOS", valor_padrao=90.0
        )

        self.maximo_entradas_por_categoria_ciclo = self._buscar_inteiro(
            nome="MAXIMO_ENTRADAS_POR_CATEGORIA_CICLO", valor_padrao=2
        )

        self.cooldown_categoria_minutos = self._buscar_decimal(
            nome="COOLDOWN_CATEGORIA_MINUTOS", valor_padrao=12.0
        )

        self.cooldown_marca_minutos = self._buscar_decimal(
            nome="COOLDOWN_MARCA_MINUTOS", valor_padrao=8.0
        )

        self.cooldown_canonico_minutos = self._buscar_decimal(
            nome="COOLDOWN_CANONICO_MINUTOS", valor_padrao=180.0
        )

        self.cooldown_familia_minutos = self._buscar_decimal(
            nome="COOLDOWN_FAMILIA_MINUTOS", valor_padrao=720.0
        )

        self.queda_minima_repost_familia_percentual = self._buscar_decimal(
            nome="QUEDA_MINIMA_REPOST_FAMILIA_PERCENTUAL", valor_padrao=5.0
        )

        self.bloqueio_categoria_minutos = self._buscar_decimal(
            nome="BLOQUEIO_CATEGORIA_MINUTOS", valor_padrao=8.0
        )

        self.janela_saturacao_categoria_minutos = self._buscar_decimal(
            nome="JANELA_SATURACAO_CATEGORIA_MINUTOS", valor_padrao=30.0
        )

        self.limite_categoria_janela = self._buscar_inteiro(
            nome="LIMITE_CATEGORIA_JANELA", valor_padrao=2
        )

        self.publicacao_intervalo_minimo_segundos = self._buscar_decimal(
            nome="PUBLICACAO_INTERVALO_MINIMO_SEGUNDOS", valor_padrao=55.0
        )

        self.publicacao_intervalo_maximo_segundos = self._buscar_decimal(
            nome="PUBLICACAO_INTERVALO_MAXIMO_SEGUNDOS", valor_padrao=300.0
        )

        self.publicacao_intervalo_modo_segundos = self._buscar_decimal(
            nome="PUBLICACAO_INTERVALO_MODO_SEGUNDOS", valor_padrao=130.0
        )

        self.publicacao_chance_intervalo_curto = self._buscar_decimal(
            nome="PUBLICACAO_CHANCE_INTERVALO_CURTO", valor_padrao=0.12
        )

        self.publicacao_intervalo_curto_minimo_segundos = self._buscar_decimal(
            nome="PUBLICACAO_INTERVALO_CURTO_MINIMO_SEGUNDOS", valor_padrao=20.0
        )

        self.publicacao_intervalo_curto_maximo_segundos = self._buscar_decimal(
            nome="PUBLICACAO_INTERVALO_CURTO_MAXIMO_SEGUNDOS", valor_padrao=50.0
        )

        self.publicacao_urgente_minimo_segundos = self._buscar_decimal(
            nome="PUBLICACAO_URGENTE_MINIMO_SEGUNDOS", valor_padrao=8.0
        )

        self.publicacao_urgente_maximo_segundos = self._buscar_decimal(
            nome="PUBLICACAO_URGENTE_MAXIMO_SEGUNDOS", valor_padrao=25.0
        )

        self.publicacao_atraso_inicial_segundos = self._buscar_decimal(
            nome="PUBLICACAO_ATRASO_INICIAL_SEGUNDOS", valor_padrao=15.0
        )

        self.publicador_intervalo_verificacao_segundos = self._buscar_decimal(
            nome="PUBLICADOR_INTERVALO_VERIFICACAO_SEGUNDOS", valor_padrao=2.0
        )

        self._validar()

    def _buscar_variavel_obrigatoria(self, nome: str) -> str:
        valor = os.getenv(nome)

        if not valor:
            raise ValueError(f"A variável {nome} não foi encontrada no arquivo .env.")

        return valor

    def _buscar_inteiro(self, nome: str, valor_padrao: int) -> int:
        valor = os.getenv(nome, str(valor_padrao))

        try:
            return int(valor)

        except ValueError as erro:
            raise ValueError(f"A variável {nome} precisa ser um número inteiro.") from erro

    def _buscar_booleano(self, nome: str, valor_padrao: bool) -> bool:
        valor = os.getenv(nome)

        if valor is None:
            return valor_padrao

        return valor.strip().lower() in {"1", "true", "sim", "on"}

    def _buscar_decimal(self, nome: str, valor_padrao: float) -> float:
        valor = os.getenv(nome, str(valor_padrao))

        try:
            return float(valor)

        except ValueError as erro:
            raise ValueError(f"A variável {nome} precisa ser um número.") from erro

    def _validar(self) -> None:
        if not re.fullmatch(r"[a-z0-9_-]+", self.identificador_marca):
            raise ValueError(
                "IDENTIFICADOR_MARCA deve conter somente "
                "letras minúsculas, números, hífen ou underline."
            )

        if self.limite_ofertas <= 0:
            raise ValueError("LIMITE_OFERTAS precisa ser maior que zero.")

        if self.maximo_publicacoes <= 0:
            raise ValueError("MAXIMO_PUBLICACOES precisa ser maior que zero.")

        if self.intervalo_publicacoes < 0:
            raise ValueError("INTERVALO_PUBLICACOES não pode ser negativo.")

        if not 0 <= self.desconto_minimo <= 100:
            raise ValueError("DESCONTO_MINIMO precisa estar entre 0 e 100.")

        if self.preco_maximo <= 0:
            raise ValueError("PRECO_MAXIMO precisa ser maior que zero.")

        if not 0 <= self.hora_inicio_madrugada <= 23:
            raise ValueError("HORA_INICIO_MADRUGADA precisa estar entre 0 e 23.")

        if not 0 <= self.hora_fim_madrugada <= 23:
            raise ValueError("HORA_FIM_MADRUGADA precisa estar entre 0 e 23.")

        if not 0 <= self.queda_minima_madrugada <= 100:
            raise ValueError("QUEDA_MINIMA_MADRUGADA precisa estar entre 0 e 100.")

        if not 0 <= self.pontuacao_minima_madrugada <= 100:
            raise ValueError("PONTUACAO_MINIMA_MADRUGADA precisa estar entre 0 e 100.")

        if self.registros_minimos_madrugada < 2:
            raise ValueError("REGISTROS_MINIMOS_MADRUGADA precisa ser pelo menos 2.")

        if not 0 <= self.nota_comprador_minima_madrugada <= 80:
            raise ValueError("NOTA_COMPRADOR_MINIMA_MADRUGADA precisa estar entre 0 e 80.")

        if not 0 <= self.queda_minima_menor_preco_madrugada <= 100:
            raise ValueError("QUEDA_MINIMA_MENOR_PRECO_MADRUGADA precisa estar entre 0 e 100.")

        if not 0 <= self.queda_maxima_automatica_madrugada <= 100:
            raise ValueError("QUEDA_MAXIMA_AUTOMATICA_MADRUGADA precisa estar entre 0 e 100.")

        if self.queda_maxima_automatica_madrugada <= self.queda_minima_madrugada:
            raise ValueError(
                "QUEDA_MAXIMA_AUTOMATICA_MADRUGADA precisa ser maior que " "QUEDA_MINIMA_MADRUGADA."
            )

        if not 0 <= self.queda_minima_anomalia <= 100:
            raise ValueError("QUEDA_MINIMA_ANOMALIA precisa estar entre 0 e 100.")

        if not 0 <= self.queda_minima_preco_bugado <= 100:
            raise ValueError("QUEDA_MINIMA_PRECO_BUGADO precisa estar entre 0 e 100.")

        if not 0 <= self.queda_maxima_anomalia_publicavel <= 100:
            raise ValueError("QUEDA_MAXIMA_ANOMALIA_PUBLICAVEL precisa estar entre 0 e 100.")

        if self.registros_minimos_anomalia < 2:
            raise ValueError("REGISTROS_MINIMOS_ANOMALIA precisa ser pelo menos 2.")

        if not 0 <= self.confianca_minima_anomalia <= 100:
            raise ValueError("CONFIANCA_MINIMA_ANOMALIA precisa estar entre 0 e 100.")

        if self.queda_minima_preco_bugado < self.queda_minima_anomalia:
            raise ValueError(
                "QUEDA_MINIMA_PRECO_BUGADO não pode ser menor que " "QUEDA_MINIMA_ANOMALIA."
            )

        if self.queda_maxima_anomalia_publicavel <= self.queda_minima_preco_bugado:
            raise ValueError(
                "QUEDA_MAXIMA_ANOMALIA_PUBLICAVEL precisa ser maior que "
                "QUEDA_MINIMA_PRECO_BUGADO."
            )

        if not 0 <= self.nota_minima_curadoria <= 100:
            raise ValueError("NOTA_MINIMA_CURADORIA precisa estar entre 0 e 100.")

        if not 0 <= self.confianca_minima_deduplicacao <= 100:
            raise ValueError("CONFIANCA_MINIMA_DEDUPLICACAO precisa estar entre 0 e 100.")

        if not 0 <= self.pontuacao_minima_fila <= 100:
            raise ValueError("PONTUACAO_MINIMA_FILA precisa estar entre 0 e 100.")

        if not 0 <= self.pontuacao_minima_reposicao_fila <= 100:
            raise ValueError("PONTUACAO_MINIMA_REPOSICAO_FILA precisa estar entre 0 e 100.")

        if self.pontuacao_minima_reposicao_fila > self.pontuacao_minima_fila:
            raise ValueError(
                "PONTUACAO_MINIMA_REPOSICAO_FILA não pode ser maior que " "PONTUACAO_MINIMA_FILA."
            )

        if self.alvo_minimo_pendentes_fila <= 0:
            raise ValueError("ALVO_MINIMO_PENDENTES_FILA precisa ser maior que zero.")

        if self.maximo_entradas_fila_por_ciclo <= 0:
            raise ValueError("MAXIMO_ENTRADAS_FILA_POR_CICLO precisa ser maior que zero.")

        if self.tamanho_maximo_fila <= 0:
            raise ValueError("TAMANHO_MAXIMO_FILA precisa ser maior que zero.")

        if self.maximo_entradas_por_categoria_ciclo <= 0:
            raise ValueError("MAXIMO_ENTRADAS_POR_CATEGORIA_CICLO precisa ser maior que zero.")

        if self.limite_categoria_janela <= 0:
            raise ValueError("LIMITE_CATEGORIA_JANELA precisa ser maior que zero.")

        if self.fila_idade_maxima_minutos <= 0:
            raise ValueError("FILA_IDADE_MAXIMA_MINUTOS precisa ser maior que zero.")

        for nome, valor in (
            ("COOLDOWN_CATEGORIA_MINUTOS", self.cooldown_categoria_minutos),
            ("COOLDOWN_MARCA_MINUTOS", self.cooldown_marca_minutos),
            ("COOLDOWN_CANONICO_MINUTOS", self.cooldown_canonico_minutos),
            ("COOLDOWN_FAMILIA_MINUTOS", self.cooldown_familia_minutos),
            (
                "QUEDA_MINIMA_REPOST_FAMILIA_PERCENTUAL",
                self.queda_minima_repost_familia_percentual,
            ),
            ("BLOQUEIO_CATEGORIA_MINUTOS", self.bloqueio_categoria_minutos),
            (
                "JANELA_SATURACAO_CATEGORIA_MINUTOS",
                self.janela_saturacao_categoria_minutos,
            ),
            (
                "PUBLICACAO_INTERVALO_MINIMO_SEGUNDOS",
                self.publicacao_intervalo_minimo_segundos,
            ),
            (
                "PUBLICACAO_INTERVALO_MAXIMO_SEGUNDOS",
                self.publicacao_intervalo_maximo_segundos,
            ),
            (
                "PUBLICACAO_INTERVALO_CURTO_MINIMO_SEGUNDOS",
                self.publicacao_intervalo_curto_minimo_segundos,
            ),
            (
                "PUBLICACAO_INTERVALO_CURTO_MAXIMO_SEGUNDOS",
                self.publicacao_intervalo_curto_maximo_segundos,
            ),
            (
                "PUBLICACAO_URGENTE_MINIMO_SEGUNDOS",
                self.publicacao_urgente_minimo_segundos,
            ),
            (
                "PUBLICACAO_URGENTE_MAXIMO_SEGUNDOS",
                self.publicacao_urgente_maximo_segundos,
            ),
            (
                "PUBLICADOR_INTERVALO_VERIFICACAO_SEGUNDOS",
                self.publicador_intervalo_verificacao_segundos,
            ),
        ):
            if valor <= 0:
                raise ValueError(f"{nome} precisa ser maior que zero.")

        if self.publicacao_intervalo_maximo_segundos < self.publicacao_intervalo_minimo_segundos:
            raise ValueError(
                "PUBLICACAO_INTERVALO_MAXIMO_SEGUNDOS não pode ser menor que "
                "PUBLICACAO_INTERVALO_MINIMO_SEGUNDOS."
            )

        if not (
            self.publicacao_intervalo_minimo_segundos
            <= self.publicacao_intervalo_modo_segundos
            <= self.publicacao_intervalo_maximo_segundos
        ):
            raise ValueError(
                "PUBLICACAO_INTERVALO_MODO_SEGUNDOS precisa ficar entre " "o mínimo e o máximo."
            )

        if not 0 <= self.publicacao_chance_intervalo_curto <= 1:
            raise ValueError("PUBLICACAO_CHANCE_INTERVALO_CURTO precisa ficar entre 0 e 1.")
