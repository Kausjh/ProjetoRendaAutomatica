# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass

from models.oferta import Oferta


@dataclass(frozen=True, slots=True)
class ResultadoFonteHunterV2:
    fonte: str
    limite_solicitado: int
    quantidade_coletada: int
    erro: str | None = None
    quantidade_novas: int = 0
    quantidade_duplicadas: int = 0

    @property
    def sucesso(self) -> bool:
        return self.erro is None

    @property
    def taxa_novidade_percentual(self) -> float:
        if self.quantidade_coletada <= 0:
            return 0.0

        return round(
            (self.quantidade_novas / self.quantidade_coletada) * 100,
            2,
        )


@dataclass(frozen=True, slots=True)
class CandidatoHunterV2:
    oferta: Oferta
    fontes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DuplicataHunterV2:
    oferta: Oferta
    representante: Oferta
    fonte: str
    tipo_identidade: str


@dataclass(frozen=True, slots=True)
class ResultadoHunterV2:
    candidatos: tuple[CandidatoHunterV2, ...]
    fontes: tuple[ResultadoFonteHunterV2, ...]
    duplicatas: tuple[DuplicataHunterV2, ...]
    quantidade_bruta: int
    quantidade_unica: int
    duplicadas_confirmadas: int

    @property
    def ofertas(self) -> list[Oferta]:
        return [candidato.oferta for candidato in self.candidatos]

    @property
    def fontes_com_erro(self) -> tuple[str, ...]:
        return tuple(resultado.fonte for resultado in self.fontes if not resultado.sucesso)

    @property
    def quantidade_candidatos_multifonte(self) -> int:
        return sum(1 for candidato in self.candidatos if len(candidato.fontes) > 1)
