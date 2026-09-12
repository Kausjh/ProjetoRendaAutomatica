# 63.8738, -149.7525

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections.abc import Callable
from datetime import datetime
from threading import RLock
from typing import Any
from urllib.parse import urlparse

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)

logger = logging.getLogger(__name__)

CHAVE_OBSERVABILIDADE_MONETIZACAO = "observabilidade_monetizacao_v1"
SCHEMA_VERSION_OBSERVABILIDADE_MONETIZACAO = 1


class EstadoObservabilidadeMonetizacaoInvalido(RuntimeError):
    pass


class ObservadorMonetizacao:
    def __init__(
        self,
        repositorio: ControleAdministrativoRepository | None = None,
        agora: Callable[[], datetime] | None = None,
    ) -> None:
        self.repositorio = (
            repositorio if repositorio is not None else ControleAdministrativoRepository()
        )
        self._agora = agora if agora is not None else lambda: datetime.now().astimezone()
        self._lock = RLock()

        with self._lock:
            if self.repositorio.obter_estado(CHAVE_OBSERVABILIDADE_MONETIZACAO) is None:
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

    @staticmethod
    def _novo_contador() -> dict[str, int]:
        return {
            "processamentos": 0,
            "transformados": 0,
            "bloqueios": 0,
            "pass_through": 0,
            "retries": 0,
            "retry_minutos_total": 0,
        }

    def _novo_estado(self) -> dict[str, Any]:
        agora = self._agora_normalizado()

        return {
            "schema_version": (SCHEMA_VERSION_OBSERVABILIDADE_MONETIZACAO),
            "iniciado_em": agora.isoformat(timespec="seconds"),
            "atualizado_em": agora.isoformat(timespec="seconds"),
            "eventos_total": 0,
            "processamentos_total": 0,
            "transformados_total": 0,
            "bloqueios_total": 0,
            "pass_through_total": 0,
            "retries_total": 0,
            "retry_minutos_total": 0,
            "por_origem": {},
            "por_afiliador": {},
            "por_dia": {},
            "ultimo_evento_em": None,
        }

    def _salvar_estado(
        self,
        estado: dict[str, Any],
    ) -> None:
        self.repositorio.definir_estado(
            chave=CHAVE_OBSERVABILIDADE_MONETIZACAO,
            valor=json.dumps(
                estado,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
        )

    def _carregar_estado(self) -> dict[str, Any]:
        bruto = self.repositorio.obter_estado(CHAVE_OBSERVABILIDADE_MONETIZACAO)

        if bruto is None:
            raise EstadoObservabilidadeMonetizacaoInvalido("estado de monetizacao ausente")

        try:
            estado = json.loads(bruto)
        except json.JSONDecodeError as erro:
            raise EstadoObservabilidadeMonetizacaoInvalido(
                "estado de monetizacao possui JSON invalido"
            ) from erro

        if not isinstance(estado, dict):
            raise EstadoObservabilidadeMonetizacaoInvalido(
                "estado de monetizacao precisa ser objeto"
            )

        if estado.get("schema_version") != SCHEMA_VERSION_OBSERVABILIDADE_MONETIZACAO:
            raise EstadoObservabilidadeMonetizacaoInvalido("schema de monetizacao incompativel")

        for campo in (
            "processamentos_total",
            "transformados_total",
            "bloqueios_total",
            "pass_through_total",
            "retries_total",
            "por_origem",
            "por_afiliador",
            "por_dia",
        ):
            if campo not in estado:
                raise EstadoObservabilidadeMonetizacaoInvalido(
                    "estado de monetizacao incompleto: " + campo
                )

        return estado

    @staticmethod
    def _normalizar_rotulo(
        valor: str | None,
        *,
        padrao: str,
    ) -> str:
        texto = str(valor or "").strip().casefold()

        if not texto:
            return padrao

        texto = unicodedata.normalize("NFKD", texto)
        texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
        texto = re.sub(r"[^a-z0-9]+", "_", texto)
        texto = texto.strip("_")

        return texto or padrao

    @staticmethod
    def _obter_host(link: str) -> str:
        if not isinstance(link, str):
            return ""

        host = (urlparse(link.strip()).hostname or "").lower()

        if host.startswith("www."):
            host = host[4:]

        return host

    @classmethod
    def _classificar_origem(
        cls,
        link: str,
    ) -> str:
        host = cls._obter_host(link)

        if (
            host == "mercadolivre.com.br"
            or host.endswith(".mercadolivre.com.br")
            or host == "meli.la"
        ):
            return "mercado_livre"

        if host == "shopee.com.br" or host.endswith(".shopee.com.br"):
            return "shopee"

        if (
            host == "amazon.com.br"
            or host.endswith(".amazon.com.br")
            or host in {"amzn.to", "link.amazon"}
        ):
            return "amazon"

        if host == "aliexpress.com" or host.endswith(".aliexpress.com"):
            return "aliexpress"

        if host == "kabum.com.br" or host.endswith(".kabum.com.br"):
            return "kabum"

        if host in {"tidd.ly", "awin1.com"}:
            return "awin"

        return "outro"

    @classmethod
    def _garantir_contador(
        cls,
        colecao: dict[str, Any],
        chave: str,
    ) -> dict[str, int]:
        atual = colecao.get(chave)

        if not isinstance(atual, dict):
            atual = cls._novo_contador()
            colecao[chave] = atual

        for campo, valor in cls._novo_contador().items():
            atual.setdefault(campo, valor)

        return atual

    @staticmethod
    def _incrementar(
        contador: dict[str, int],
        campo: str,
        quantidade: int = 1,
    ) -> None:
        contador[campo] = int(contador.get(campo, 0)) + int(quantidade)

    def registrar_processamento(
        self,
        *,
        link_original: str,
        afiliador: str,
        transformado: bool,
        exige_confirmacao: bool,
    ) -> None:
        agora = self._agora_normalizado()
        origem = self._classificar_origem(link_original)
        afiliador_normalizado = self._normalizar_rotulo(
            afiliador,
            padrao="nenhum",
        )

        if transformado:
            evento = "transformados"
        elif exige_confirmacao:
            evento = "bloqueios"
        else:
            evento = "pass_through"

        with self._lock:
            estado = self._carregar_estado()

            self._incrementar(
                estado,
                "eventos_total",
            )
            self._incrementar(
                estado,
                "processamentos_total",
            )
            self._incrementar(
                estado,
                evento + "_total",
            )

            por_origem = self._garantir_contador(
                estado["por_origem"],
                origem,
            )
            self._incrementar(
                por_origem,
                "processamentos",
            )
            self._incrementar(
                por_origem,
                evento,
            )

            por_afiliador = self._garantir_contador(
                estado["por_afiliador"],
                afiliador_normalizado,
            )
            self._incrementar(
                por_afiliador,
                "processamentos",
            )
            self._incrementar(
                por_afiliador,
                evento,
            )

            dia = agora.date().isoformat()
            por_dia = self._garantir_contador(
                estado["por_dia"],
                dia,
            )
            self._incrementar(
                por_dia,
                "processamentos",
            )
            self._incrementar(
                por_dia,
                evento,
            )

            timestamp = agora.isoformat(timespec="seconds")
            estado["atualizado_em"] = timestamp
            estado["ultimo_evento_em"] = timestamp

            self._salvar_estado(estado)

    def registrar_processamento_seguro(
        self,
        **kwargs: Any,
    ) -> None:
        try:
            self.registrar_processamento(**kwargs)
        except Exception:
            logger.warning(
                "Falha ao registrar observabilidade " "de monetizacao.",
                exc_info=True,
            )

    def registrar_retry(
        self,
        *,
        link_original: str,
        minutos: int,
    ) -> None:
        minutos_validos = max(
            0,
            int(minutos),
        )
        agora = self._agora_normalizado()
        origem = self._classificar_origem(link_original)

        with self._lock:
            estado = self._carregar_estado()

            self._incrementar(
                estado,
                "eventos_total",
            )
            self._incrementar(
                estado,
                "retries_total",
            )
            self._incrementar(
                estado,
                "retry_minutos_total",
                minutos_validos,
            )

            por_origem = self._garantir_contador(
                estado["por_origem"],
                origem,
            )
            self._incrementar(
                por_origem,
                "retries",
            )
            self._incrementar(
                por_origem,
                "retry_minutos_total",
                minutos_validos,
            )

            dia = agora.date().isoformat()
            por_dia = self._garantir_contador(
                estado["por_dia"],
                dia,
            )
            self._incrementar(
                por_dia,
                "retries",
            )
            self._incrementar(
                por_dia,
                "retry_minutos_total",
                minutos_validos,
            )

            timestamp = agora.isoformat(timespec="seconds")
            estado["atualizado_em"] = timestamp
            estado["ultimo_evento_em"] = timestamp

            self._salvar_estado(estado)

    def registrar_retry_seguro(
        self,
        **kwargs: Any,
    ) -> None:
        try:
            self.registrar_retry(**kwargs)
        except Exception:
            logger.warning(
                "Falha ao registrar retry " "de monetizacao.",
                exc_info=True,
            )

    def obter_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return json.loads(
                json.dumps(
                    self._carregar_estado(),
                    ensure_ascii=False,
                )
            )
