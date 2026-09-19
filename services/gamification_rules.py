from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RegraGamificacao:
    tipo_evento: str
    xp_delta: int = 0
    reputacao_delta: int = 0
    limite_por_janela: int | None = None
    janela_segundos: int | None = None

    def __post_init__(self) -> None:
        tipo = self.tipo_evento.strip()

        if not tipo:
            raise ValueError("tipo_evento nao pode ser vazio.")

        if tipo != self.tipo_evento:
            raise ValueError("tipo_evento precisa estar normalizado.")

        if self.xp_delta < 0:
            raise ValueError("xp_delta nao pode ser negativo.")

        limite_definido = self.limite_por_janela is not None
        janela_definida = self.janela_segundos is not None

        if limite_definido != janela_definida:
            raise ValueError(
                "limite_por_janela e janela_segundos " "precisam ser definidos juntos."
            )

        if self.limite_por_janela is not None and self.limite_por_janela <= 0:
            raise ValueError("limite_por_janela precisa ser positivo.")

        if self.janela_segundos is not None and self.janela_segundos <= 0:
            raise ValueError("janela_segundos precisa ser positivo.")


@dataclass(frozen=True, slots=True)
class ConjuntoRegrasGamificacao:
    versao: str
    regras: tuple[RegraGamificacao, ...]
    niveis_xp: tuple[int, ...] = (0,)

    def __post_init__(self) -> None:
        versao = self.versao.strip()

        if not versao:
            raise ValueError("versao nao pode ser vazia.")

        if versao != self.versao:
            raise ValueError("versao precisa estar normalizada.")

        tipos = [regra.tipo_evento for regra in self.regras]

        if len(tipos) != len(set(tipos)):
            raise ValueError("tipos de evento duplicados no ruleset.")

        if not self.niveis_xp or self.niveis_xp[0] != 0:
            raise ValueError("niveis_xp precisa iniciar em zero.")

        if any(valor < 0 for valor in self.niveis_xp):
            raise ValueError("niveis_xp nao pode conter " "valores negativos.")

        if tuple(sorted(set(self.niveis_xp))) != self.niveis_xp:
            raise ValueError("niveis_xp precisa ser " "estritamente crescente " "e sem duplicatas.")

    def obter_regra(
        self,
        tipo_evento: str,
    ) -> RegraGamificacao | None:
        tipo = str(tipo_evento or "").strip()

        for regra in self.regras:
            if regra.tipo_evento == tipo:
                return regra

        return None

    def calcular_nivel(
        self,
        xp_total: int,
    ) -> int:
        xp = max(
            int(xp_total),
            0,
        )

        return bisect_right(
            self.niveis_xp,
            xp,
        )
