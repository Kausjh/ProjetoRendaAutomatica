# 63.8738, -149.7525

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EstadoServicoNode:
    nome: str
    ativo: bool
    pids: tuple[int, ...] = ()
    detalhes: str | None = None
    memoria_rss_bytes: int | None = None

    def para_dict(self) -> dict[str, Any]:
        return {
            "nome": self.nome,
            "ativo": self.ativo,
            "pids": list(self.pids),
            "detalhes": self.detalhes,
            "memoria_rss_bytes": self.memoria_rss_bytes,
        }


@dataclass(frozen=True, slots=True)
class EstadoNode:
    versao_schema: int
    node_id: str
    coletado_em: str

    sistema: str
    versao_sistema: str
    arquitetura: str

    uptime_segundos: float | None

    cpu_percentual: float | None

    memoria_total_bytes: int | None
    memoria_disponivel_bytes: int | None
    memoria_uso_percentual: float | None

    disco_total_bytes: int | None
    disco_livre_bytes: int | None
    disco_uso_percentual: float | None

    quantidade_processos_projeto: int

    servicos: tuple[EstadoServicoNode, ...]

    memoria_processos_projeto_bytes: int | None = None

    def para_dict(self) -> dict[str, Any]:
        return {
            "versao_schema": self.versao_schema,
            "node_id": self.node_id,
            "coletado_em": self.coletado_em,
            "sistema": self.sistema,
            "versao_sistema": self.versao_sistema,
            "arquitetura": self.arquitetura,
            "uptime_segundos": self.uptime_segundos,
            "cpu_percentual": self.cpu_percentual,
            "memoria_total_bytes": self.memoria_total_bytes,
            "memoria_disponivel_bytes": self.memoria_disponivel_bytes,
            "memoria_uso_percentual": self.memoria_uso_percentual,
            "disco_total_bytes": self.disco_total_bytes,
            "disco_livre_bytes": self.disco_livre_bytes,
            "disco_uso_percentual": self.disco_uso_percentual,
            "quantidade_processos_projeto": (self.quantidade_processos_projeto),
            "memoria_processos_projeto_bytes": (self.memoria_processos_projeto_bytes),
            "servicos": [servico.para_dict() for servico in self.servicos],
        }
