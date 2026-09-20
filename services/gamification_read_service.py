from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from models.gamification import (
    PerfilGamificacao,
)
from services.gamification_achievements import (
    EstadoConquistaGamificacao,
    avaliar_conquistas,
)
from services.gamification_service import (
    GamificationService,
)

_EVENT_PAGE_SIZE = 200


@dataclass(frozen=True, slots=True)
class ProgressoNivelGamificacao:
    nivel_atual: int
    xp_total: int
    xp_inicio_nivel: int
    xp_proximo_nivel: int | None
    xp_no_nivel: int
    xp_necessario_no_nivel: int | None
    xp_faltante: int
    percentual: float
    nivel_maximo: bool


@dataclass(frozen=True, slots=True)
class LeituraGamificacaoUsuario:
    perfil: PerfilGamificacao
    progresso_nivel: ProgressoNivelGamificacao
    conquistas: tuple[
        EstadoConquistaGamificacao,
        ...,
    ]
    badges_desbloqueadas: tuple[str, ...]
    ruleset_version: str


class GamificationReadService:
    def __init__(
        self,
        gamification_service: GamificationService,
    ) -> None:
        self.gamification_service = gamification_service

    def _contagens_eventos(
        self,
        conta_id: str,
    ) -> dict[str, int]:
        contagens: Counter[str] = Counter()
        offset = 0

        while True:
            eventos = self.gamification_service.listar_eventos(
                conta_id,
                limite=_EVENT_PAGE_SIZE,
                offset=offset,
            )

            for evento in eventos:
                contagens[evento.tipo_evento] += 1

            if len(eventos) < _EVENT_PAGE_SIZE:
                break

            offset += len(eventos)

        return dict(contagens)

    def _progresso_nivel(
        self,
        perfil: PerfilGamificacao,
    ) -> ProgressoNivelGamificacao:
        thresholds = tuple(int(valor) for valor in (self.gamification_service.ruleset.niveis_xp))

        if not thresholds:
            raise RuntimeError("Ruleset sem thresholds de nivel.")

        nivel = max(
            int(perfil.nivel),
            1,
        )

        indice_inicio = min(
            nivel - 1,
            len(thresholds) - 1,
        )

        xp_inicio = thresholds[indice_inicio]

        nivel_maximo = nivel >= len(thresholds)

        if nivel_maximo:
            return ProgressoNivelGamificacao(
                nivel_atual=nivel,
                xp_total=int(perfil.xp_total),
                xp_inicio_nivel=xp_inicio,
                xp_proximo_nivel=None,
                xp_no_nivel=max(
                    int(perfil.xp_total) - xp_inicio,
                    0,
                ),
                xp_necessario_no_nivel=None,
                xp_faltante=0,
                percentual=100.0,
                nivel_maximo=True,
            )

        xp_proximo = thresholds[nivel]

        necessario = xp_proximo - xp_inicio

        xp_no_nivel = min(
            max(
                int(perfil.xp_total) - xp_inicio,
                0,
            ),
            necessario,
        )

        faltante = max(
            xp_proximo - int(perfil.xp_total),
            0,
        )

        percentual = round(
            (xp_no_nivel / necessario * 100.0),
            2,
        )

        return ProgressoNivelGamificacao(
            nivel_atual=nivel,
            xp_total=int(perfil.xp_total),
            xp_inicio_nivel=xp_inicio,
            xp_proximo_nivel=xp_proximo,
            xp_no_nivel=xp_no_nivel,
            xp_necessario_no_nivel=(necessario),
            xp_faltante=faltante,
            percentual=percentual,
            nivel_maximo=False,
        )

    def obter(
        self,
        conta_id: str,
    ) -> LeituraGamificacaoUsuario:
        perfil = self.gamification_service.obter_perfil(conta_id)

        contagens = self._contagens_eventos(conta_id)

        conquistas = avaliar_conquistas(
            perfil=perfil,
            contagens_eventos=contagens,
        )

        badges = tuple(item.badge for item in conquistas if item.desbloqueada)

        return LeituraGamificacaoUsuario(
            perfil=perfil,
            progresso_nivel=(self._progresso_nivel(perfil)),
            conquistas=conquistas,
            badges_desbloqueadas=badges,
            ruleset_version=(self.gamification_service.ruleset.versao),
        )
