# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass

from models.oferta import Oferta
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from models.resultado_validacao_preco_social_scout import (
    ResultadoValidacaoPrecoSocialScout,
)


@dataclass(frozen=True, slots=True)
class ResultadoCommunityDiscoveryAdapter:
    status: str
    marketplace: str | None
    motivo: str

    oferta: Oferta | None = None

    resolucao: ResultadoResolucaoSocialScout | None = None
    validacao: ResultadoValidacaoPrecoSocialScout | None = None

    transitorio: bool = False
