from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DefinicaoMissao:
    codigo: str
    titulo: str
    descricao: str
    tipo_evento: str
    alvo: int
    recompensa_xp: int
    incremento_por_evento: int = 1

    def __post_init__(self) -> None:
        if not self.codigo.strip():
            raise ValueError("codigo da missao nao pode ser vazio.")

        if not self.titulo.strip():
            raise ValueError("titulo da missao nao pode ser vazio.")

        if not self.tipo_evento.strip():
            raise ValueError("tipo_evento nao pode ser vazio.")

        if self.alvo < 1:
            raise ValueError("alvo precisa ser positivo.")

        if self.recompensa_xp < 1:
            raise ValueError("recompensa_xp precisa ser positiva.")

        if self.incremento_por_evento < 1:
            raise ValueError("incremento_por_evento " "precisa ser positivo.")


@dataclass(frozen=True, slots=True)
class ConjuntoRegrasMissoes:
    versao: str
    missoes: tuple[DefinicaoMissao, ...]

    def __post_init__(self) -> None:
        if not self.versao.strip():
            raise ValueError("versao do ruleset nao pode ser vazia.")

        codigos = [missao.codigo for missao in self.missoes]

        if len(codigos) != len(set(codigos)):
            raise ValueError("codigos de missao precisam ser unicos.")

    def obter(
        self,
        codigo: str,
    ) -> DefinicaoMissao | None:
        codigo_normalizado = str(codigo or "").strip()

        for missao in self.missoes:
            if missao.codigo == codigo_normalizado:
                return missao

        return None

    def listar_por_evento(
        self,
        tipo_evento: str,
    ) -> tuple[DefinicaoMissao, ...]:
        tipo = str(tipo_evento or "").strip()

        return tuple(missao for missao in self.missoes if missao.tipo_evento == tipo)
