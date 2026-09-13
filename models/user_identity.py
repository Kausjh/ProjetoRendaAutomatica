from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContaUsuario:
    id: str
    email: str
    criado_em: str
    ativa: bool


@dataclass(frozen=True, slots=True)
class SessaoUsuario:
    id: str
    conta_id: str
    criado_em: str
    expira_em: str
    revogada_em: str | None


@dataclass(frozen=True, slots=True)
class SessaoUsuarioEmitida:
    conta: ContaUsuario
    sessao: SessaoUsuario
    token: str
