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

    @property
    def sucesso(self) -> bool:
        return self.erro is None


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
