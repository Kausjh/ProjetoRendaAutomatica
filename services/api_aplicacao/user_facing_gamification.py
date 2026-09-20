from __future__ import annotations

from models.user_identity import (
    ContaUsuario,
)
from services.api_aplicacao.user_facing_http import (
    ErroHttpUserFacing,
)
from services.gamification_read_service import (
    GamificationReadService,
    LeituraGamificacaoUsuario,
)
from services.gamification_service import (
    ContaGamificacaoInvalida,
)


class UserFacingGamificationController:
    def __init__(
        self,
        gamification_read_service: GamificationReadService | None,
    ) -> None:
        self.gamification_read_service = gamification_read_service

    def _service(
        self,
    ) -> GamificationReadService:
        service = self.gamification_read_service

        if service is None:
            raise ErroHttpUserFacing(
                503,
                "gamificacao_indisponivel",
                "Gamificacao indisponivel.",
            )

        return service

    @staticmethod
    def _serializar(
        leitura: LeituraGamificacaoUsuario,
    ) -> dict[str, object]:
        perfil = leitura.perfil
        progresso = leitura.progresso_nivel

        return {
            "perfil": {
                "xp_total": perfil.xp_total,
                "nivel": perfil.nivel,
                "reputacao_total": (perfil.reputacao_total),
                "eventos_total": (perfil.eventos_total),
                "atualizado_em": (perfil.atualizado_em),
            },
            "progresso_nivel": {
                "nivel_atual": (progresso.nivel_atual),
                "xp_total": (progresso.xp_total),
                "xp_inicio_nivel": (progresso.xp_inicio_nivel),
                "xp_proximo_nivel": (progresso.xp_proximo_nivel),
                "xp_no_nivel": (progresso.xp_no_nivel),
                "xp_necessario_no_nivel": (progresso.xp_necessario_no_nivel),
                "xp_faltante": (progresso.xp_faltante),
                "percentual": (progresso.percentual),
                "nivel_maximo": (progresso.nivel_maximo),
            },
            "conquistas": [
                {
                    "codigo": item.codigo,
                    "nome": item.nome,
                    "descricao": (item.descricao),
                    "badge": item.badge,
                    "desbloqueada": (item.desbloqueada),
                    "progresso_atual": (item.progresso_atual),
                    "progresso_alvo": (item.progresso_alvo),
                }
                for item in leitura.conquistas
            ],
            "badges_desbloqueadas": list(leitura.badges_desbloqueadas),
            "ruleset_version": (leitura.ruleset_version),
        }

    def obter(
        self,
        conta: ContaUsuario,
    ) -> tuple[int, dict[str, object]]:
        try:
            leitura = self._service().obter(conta.id)

        except ContaGamificacaoInvalida as erro:
            raise ErroHttpUserFacing(
                401,
                "sessao_usuario_invalida",
                "Sessao de usuario invalida.",
            ) from erro

        except ValueError as erro:
            raise ErroHttpUserFacing(
                400,
                "gamificacao_invalida",
                str(erro),
            ) from erro

        return (
            200,
            self._serializar(leitura),
        )
