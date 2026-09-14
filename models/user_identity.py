from __future__ import annotations

from dataclasses import dataclass, field


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


@dataclass(frozen=True, slots=True)
class DispositivoUsuario:
    id: str
    conta_id: str
    instalacao_id: str
    plataforma: str
    push_token: str = field(repr=False)
    ativo: bool
    criado_em: str
    atualizado_em: str
    revogado_em: str | None
