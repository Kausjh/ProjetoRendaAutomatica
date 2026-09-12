# 63.8738, -149.7525

from __future__ import annotations

import json
import math
from collections.abc import Callable
from datetime import datetime, timedelta
from threading import RLock
from typing import Any

from models.inteligencia_ai import SolicitacaoInteligenciaAI
from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)

CHAVE_ESTADO_SHADOW_AI = "shadow_ai_v1"
SCHEMA_VERSION_SHADOW_AI = 1
DURACAO_SHADOW_DIAS = 7

MODELO_REFERENCIA_SHADOW_AI = "gpt-5.6-luna"
CUSTO_ENTRADA_USD_POR_MILHAO = 0.20
CUSTO_SAIDA_USD_POR_MILHAO = 1.20

CARACTERES_UTF8_POR_TOKEN_ESTIMADO = 3
OVERHEAD_ENTRADA_TOKENS_ESTIMADO = 180

TOKENS_SAIDA_ESTIMADOS_POR_TAREFA = {
    "desambiguar_categoria_produto": 80,
    "interpretar_incerteza_editorial": 120,
}

CONSUMIDORES_VALIDOS = {
    "classificador",
    "curadoria",
}


class EstadoShadowAIInvalido(RuntimeError):
    pass


class ObservadorShadowAI:
    # Observa gates que teriam usado IA sem chamar provider algum.
    # O estado e agregado; titulos e payloads completos nao sao persistidos.

    def __init__(
        self,
        *,
        repositorio: ControleAdministrativoRepository | None = None,
        agora: Callable[[], datetime] | None = None,
        duracao_dias: int = DURACAO_SHADOW_DIAS,
    ) -> None:
        if isinstance(duracao_dias, bool) or not isinstance(duracao_dias, int) or duracao_dias <= 0:
            raise ValueError("duracao_dias precisa ser inteiro positivo")

        self.repositorio = (
            repositorio if repositorio is not None else ControleAdministrativoRepository()
        )
        self._agora = agora if agora is not None else lambda: datetime.now().astimezone()
        self.duracao_dias = duracao_dias
        self._lock = RLock()

        with self._lock:
            if self.repositorio.obter_estado(CHAVE_ESTADO_SHADOW_AI) is None:
                self._salvar_estado(self._novo_estado())
            else:
                self._carregar_estado()

    def _agora_normalizado(self) -> datetime:
        valor = self._agora()
        if not isinstance(valor, datetime):
            raise TypeError("agora precisa retornar datetime")
        if valor.tzinfo is None:
            raise ValueError("agora precisa retornar datetime com timezone")
        return valor

    def _novo_estado(self) -> dict[str, Any]:
        agora = self._agora_normalizado()
        termina = agora + timedelta(days=self.duracao_dias)
        return {
            "schema_version": SCHEMA_VERSION_SHADOW_AI,
            "modo": "shadow",
            "iniciado_em": agora.isoformat(timespec="seconds"),
            "termina_em": termina.isoformat(timespec="seconds"),
            "duracao_dias": self.duracao_dias,
            "concluido": False,
            "modelo_referencia": MODELO_REFERENCIA_SHADOW_AI,
            "precos_referencia_usd_por_milhao": {
                "entrada": CUSTO_ENTRADA_USD_POR_MILHAO,
                "saida": CUSTO_SAIDA_USD_POR_MILHAO,
            },
            "eventos_total": 0,
            "por_consumidor": {
                "classificador": self._novo_agregado(),
                "curadoria": self._novo_agregado(),
            },
            "por_dia": {},
            "estimativas": self._novo_agregado(),
            "ultimo_evento_em": None,
        }

    @staticmethod
    def _novo_agregado() -> dict[str, Any]:
        return {
            "eventos": 0,
            "tokens_entrada": 0,
            "tokens_saida": 0,
            "tokens_total": 0,
            "custo_usd": 0.0,
        }

    def _salvar_estado(self, estado: dict[str, Any]) -> None:
        self.repositorio.definir_estado(
            chave=CHAVE_ESTADO_SHADOW_AI,
            valor=json.dumps(
                estado,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )

    def _carregar_estado(self) -> dict[str, Any]:
        bruto = self.repositorio.obter_estado(CHAVE_ESTADO_SHADOW_AI)
        if bruto is None:
            raise EstadoShadowAIInvalido("estado shadow AI ausente")
        try:
            estado = json.loads(bruto)
        except json.JSONDecodeError as erro:
            raise EstadoShadowAIInvalido("estado shadow AI possui JSON invalido") from erro
        if not isinstance(estado, dict):
            raise EstadoShadowAIInvalido("estado shadow AI precisa ser objeto")
        if estado.get("schema_version") != SCHEMA_VERSION_SHADOW_AI:
            raise EstadoShadowAIInvalido("schema shadow AI incompativel")
        if estado.get("modo") != "shadow":
            raise EstadoShadowAIInvalido("modo shadow AI invalido")
        for campo in (
            "iniciado_em",
            "termina_em",
            "por_consumidor",
            "por_dia",
            "estimativas",
        ):
            if campo not in estado:
                raise EstadoShadowAIInvalido("estado shadow AI incompleto: " + campo)
        return estado

    @staticmethod
    def _parsear_data(valor: str) -> datetime:
        try:
            data = datetime.fromisoformat(valor)
        except (TypeError, ValueError) as erro:
            raise EstadoShadowAIInvalido("timestamp shadow AI invalido") from erro
        if data.tzinfo is None:
            raise EstadoShadowAIInvalido("timestamp shadow AI sem timezone")
        return data

    def _atualizar_conclusao(
        self,
        estado: dict[str, Any],
        *,
        agora: datetime,
    ) -> bool:
        termina = self._parsear_data(estado["termina_em"])
        concluido = agora >= termina
        if bool(estado.get("concluido")) != concluido:
            estado["concluido"] = concluido
            return True
        return False

    @staticmethod
    def _estimar_tokens_entrada(
        solicitacao: SolicitacaoInteligenciaAI,
    ) -> int:
        payload = json.dumps(
            {
                "tarefa": solicitacao.tarefa,
                "contexto": solicitacao.contexto,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        bytes_utf8 = len(payload.encode("utf-8"))
        tokens_payload = math.ceil(bytes_utf8 / CARACTERES_UTF8_POR_TOKEN_ESTIMADO)
        return OVERHEAD_ENTRADA_TOKENS_ESTIMADO + tokens_payload

    @staticmethod
    def _estimar_tokens_saida(
        solicitacao: SolicitacaoInteligenciaAI,
    ) -> int:
        return TOKENS_SAIDA_ESTIMADOS_POR_TAREFA.get(solicitacao.tarefa, 120)

    @staticmethod
    def _estimar_custo_usd(
        *,
        tokens_entrada: int,
        tokens_saida: int,
    ) -> float:
        custo_entrada = tokens_entrada * CUSTO_ENTRADA_USD_POR_MILHAO / 1_000_000
        custo_saida = tokens_saida * CUSTO_SAIDA_USD_POR_MILHAO / 1_000_000
        return round(custo_entrada + custo_saida, 10)

    @staticmethod
    def _somar_agregado(
        agregado: dict[str, Any],
        *,
        tokens_entrada: int,
        tokens_saida: int,
        custo_usd: float,
    ) -> None:
        agregado["eventos"] = int(agregado.get("eventos", 0)) + 1
        agregado["tokens_entrada"] = int(agregado.get("tokens_entrada", 0)) + tokens_entrada
        agregado["tokens_saida"] = int(agregado.get("tokens_saida", 0)) + tokens_saida
        agregado["tokens_total"] = (
            int(agregado.get("tokens_total", 0)) + tokens_entrada + tokens_saida
        )
        agregado["custo_usd"] = round(
            float(agregado.get("custo_usd", 0.0)) + custo_usd,
            10,
        )

    def registrar_gate(
        self,
        *,
        consumidor: str,
        solicitacao: SolicitacaoInteligenciaAI,
    ) -> bool:
        if consumidor not in CONSUMIDORES_VALIDOS:
            raise ValueError("consumidor shadow AI invalido")
        if not isinstance(solicitacao, SolicitacaoInteligenciaAI):
            raise TypeError("solicitacao precisa ser SolicitacaoInteligenciaAI")

        with self._lock:
            estado = self._carregar_estado()
            agora = self._agora_normalizado()

            if self._atualizar_conclusao(estado, agora=agora):
                self._salvar_estado(estado)

            if estado["concluido"]:
                return False

            tokens_entrada = self._estimar_tokens_entrada(solicitacao)
            tokens_saida = self._estimar_tokens_saida(solicitacao)
            custo_usd = self._estimar_custo_usd(
                tokens_entrada=tokens_entrada,
                tokens_saida=tokens_saida,
            )

            estado["eventos_total"] = int(estado.get("eventos_total", 0)) + 1

            self._somar_agregado(
                estado["por_consumidor"][consumidor],
                tokens_entrada=tokens_entrada,
                tokens_saida=tokens_saida,
                custo_usd=custo_usd,
            )

            dia = agora.date().isoformat()
            por_dia = estado["por_dia"]
            if dia not in por_dia:
                por_dia[dia] = {
                    "total": self._novo_agregado(),
                    "classificador": self._novo_agregado(),
                    "curadoria": self._novo_agregado(),
                }

            self._somar_agregado(
                por_dia[dia]["total"],
                tokens_entrada=tokens_entrada,
                tokens_saida=tokens_saida,
                custo_usd=custo_usd,
            )
            self._somar_agregado(
                por_dia[dia][consumidor],
                tokens_entrada=tokens_entrada,
                tokens_saida=tokens_saida,
                custo_usd=custo_usd,
            )
            self._somar_agregado(
                estado["estimativas"],
                tokens_entrada=tokens_entrada,
                tokens_saida=tokens_saida,
                custo_usd=custo_usd,
            )

            estado["ultimo_evento_em"] = agora.isoformat(timespec="seconds")
            self._salvar_estado(estado)
            return True

    def registrar_gate_seguro(
        self,
        *,
        consumidor: str,
        solicitacao: SolicitacaoInteligenciaAI,
    ) -> bool:
        try:
            return self.registrar_gate(
                consumidor=consumidor,
                solicitacao=solicitacao,
            )
        except Exception:
            return False

    def obter_snapshot(self) -> dict[str, Any]:
        with self._lock:
            estado = self._carregar_estado()
            agora = self._agora_normalizado()
            if self._atualizar_conclusao(estado, agora=agora):
                self._salvar_estado(estado)
            return json.loads(json.dumps(estado, ensure_ascii=False))
