from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from numbers import Real
from typing import Any

from models.observabilidade_ai import UsoInteligenciaAI


@dataclass(
    frozen=True,
    slots=True,
)
class SolicitacaoInteligenciaAI:
    tarefa: str
    contexto: Mapping[str, Any]

    def __post_init__(self) -> None:
        tarefa = str(self.tarefa or "").strip()

        if not tarefa:
            raise ValueError("tarefa precisa ser informada")

        if not isinstance(
            self.contexto,
            Mapping,
        ):
            raise TypeError("contexto precisa ser um Mapping")


@dataclass(
    frozen=True,
    slots=True,
)
class RespostaProvedorInteligenciaAI:
    conteudo: Mapping[str, Any]
    confianca: float
    provedor: str
    modelo: str | None = None
    uso: UsoInteligenciaAI | None = None

    def __post_init__(self) -> None:
        if not isinstance(
            self.conteudo,
            Mapping,
        ):
            raise TypeError("conteudo precisa ser um Mapping")

        if not isinstance(
            self.confianca,
            Real,
        ) or isinstance(
            self.confianca,
            bool,
        ):
            raise TypeError("confianca precisa ser numerica")

        confianca = float(self.confianca)

        if not 0.0 <= confianca <= 1.0:
            raise ValueError("confianca precisa ficar entre 0 e 1")

        provedor = str(self.provedor or "").strip()

        if not provedor:
            raise ValueError("provedor precisa ser informado")

        if self.uso is not None and not isinstance(
            self.uso,
            UsoInteligenciaAI,
        ):
            raise TypeError("uso precisa ser UsoInteligenciaAI ou None")


@dataclass(
    frozen=True,
    slots=True,
)
class ResultadoInteligenciaAssistivaAI:
    status: str
    sugestao: dict[str, Any]
    origem: str
    confianca: float | None
    provedor: str | None
    modelo: str | None
    fallback_usado: bool
    validada_deterministicamente: bool
    tipo_erro: str | None = None

    somente_sugestao: bool = True
    autoriza_publicacao: bool = False
    autoriza_alteracao_budget: bool = False
    substitui_regras_deterministicas: bool = False
