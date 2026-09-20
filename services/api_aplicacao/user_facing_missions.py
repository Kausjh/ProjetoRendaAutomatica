from __future__ import annotations

from typing import Any

from services.api_aplicacao.user_facing_http import (
    ErroHttpUserFacing,
)
from services.mission_read_service import (
    LeituraMissoesUsuario,
    MissionReadService,
)
from services.mission_service import (
    ContaMissaoInvalida,
)


class UserFacingMissionsController:
    def __init__(
        self,
        mission_read_service: MissionReadService | None,
    ) -> None:
        self.mission_read_service = mission_read_service

    def _service(
        self,
    ) -> MissionReadService:
        service = self.mission_read_service

        if service is None:
            raise ErroHttpUserFacing(
                503,
                "missoes_indisponiveis",
                "Missoes indisponiveis.",
            )

        return service

    @staticmethod
    def _serializar(
        leitura: LeituraMissoesUsuario,
    ) -> dict[str, object]:
        resumo = leitura.resumo

        return {
            "ruleset_version": (leitura.ruleset_version),
            "instancia_chave": (leitura.instancia_chave),
            "resumo": {
                "total": resumo.total,
                "concluidas": resumo.concluidas,
                "em_andamento": (resumo.em_andamento),
                "nao_iniciadas": (resumo.nao_iniciadas),
                "rewards_pending": (resumo.rewards_pending),
                "rewards_granted": (resumo.rewards_granted),
            },
            "missoes": [
                {
                    "codigo": item.codigo,
                    "titulo": item.titulo,
                    "descricao": item.descricao,
                    "progresso_atual": (item.progresso_atual),
                    "progresso_alvo": (item.progresso_alvo),
                    "percentual": item.percentual,
                    "concluida": item.concluida,
                    "concluida_em": (item.concluida_em),
                    "atualizado_em": (item.atualizado_em),
                    "recompensa": {
                        "tipo": (item.recompensa.tipo),
                        "quantidade": (item.recompensa.quantidade),
                        "status": (item.recompensa.status),
                        "concedida_em": (item.recompensa.concedida_em),
                    },
                }
                for item in leitura.missoes
            ],
        }

    def obter(
        self,
        conta: Any,
    ) -> tuple[int, dict[str, object]]:
        try:
            leitura = self._service().obter(conta.id)

        except ContaMissaoInvalida as erro:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            ) from erro

        except ValueError as erro:
            raise ErroHttpUserFacing(
                400,
                "missoes_invalidas",
                str(erro),
            ) from erro

        except RuntimeError as erro:
            raise ErroHttpUserFacing(
                503,
                "missoes_indisponiveis",
                "Missoes indisponiveis.",
            ) from erro

        return (
            200,
            self._serializar(leitura),
        )
