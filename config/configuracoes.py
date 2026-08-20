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
            nome="QUEDA_MINIMA_MADRUGADA", valor_padrao=15.0
        )

        self.pontuacao_minima_madrugada = self._buscar_decimal(
            nome="PONTUACAO_MINIMA_MADRUGADA", valor_padrao=80.0
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
