# 63.8738, -149.7525

from dataclasses import dataclass
from datetime import datetime

from models.perfil_comercial_scout import (
    PerfilComercialScout,
)


@dataclass(frozen=True, slots=True)
class ObservacaoComercialScout:
    """
    Um perfil comercial observado em um instante conhecido.

    O horario e obrigatorio porque tendencia exige dimensao temporal.
    """

    perfil: PerfilComercialScout
    observado_em: datetime


@dataclass(frozen=True, slots=True)
class TendenciaComercialScout:
    """
    Recorrencia comercial comprovada por multiplos sinais distintos.

    Uma instancia desta classe nunca representa apenas um sinal isolado.
    """

    dimensao: str
    chave: str
    rotulo: str

    janela_horas: int

    sinais_distintos: int
    ocorrencias_anteriores: int
    ocorrencias_recentes: int

    direcao: str

    evidencias: tuple[str, ...] = ()
