from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from models.gamification import (
    PerfilGamificacao,
)

CRITERIOS_CONQUISTA_VALIDOS = frozenset(
    {
        "event_count",
        "all_events",
        "level",
    }
)


@dataclass(frozen=True, slots=True)
class DefinicaoConquistaGamificacao:
    codigo: str
    nome: str
    descricao: str
    badge: str
    tipo_criterio: str
    alvo: int
    evento_tipo: str | None = None
    eventos_requeridos: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.codigo.strip():
            raise ValueError("codigo nao pode ser vazio.")

        if not self.nome.strip():
            raise ValueError("nome nao pode ser vazio.")

        if not self.badge.strip():
            raise ValueError("badge nao pode ser vazio.")

        if self.tipo_criterio not in CRITERIOS_CONQUISTA_VALIDOS:
            raise ValueError("tipo_criterio invalido.")

        if self.alvo <= 0:
            raise ValueError("alvo precisa ser positivo.")

        if self.tipo_criterio == "event_count" and not self.evento_tipo:
            raise ValueError("event_count exige evento_tipo.")

        if self.tipo_criterio == "all_events" and not self.eventos_requeridos:
            raise ValueError("all_events exige " "eventos_requeridos.")


@dataclass(frozen=True, slots=True)
class EstadoConquistaGamificacao:
    codigo: str
    nome: str
    descricao: str
    badge: str
    desbloqueada: bool
    progresso_atual: int
    progresso_alvo: int


CONQUISTAS_PRODUCAO_V1 = (
    DefinicaoConquistaGamificacao(
        codigo="radar_ligado",
        nome="Radar Ligado",
        descricao=("Adicione o primeiro produto " "a sua Lista."),
        badge="radar-ligado",
        tipo_criterio="event_count",
        alvo=1,
        evento_tipo=("watchlist_produto_adicionado"),
    ),
    DefinicaoConquistaGamificacao(
        codigo="lista_5",
        nome="Lista em Movimento",
        descricao=("Adicione cinco produtos " "distintos a Lista."),
        badge="lista-5",
        tipo_criterio="event_count",
        alvo=5,
        evento_tipo=("watchlist_produto_adicionado"),
    ),
    DefinicaoConquistaGamificacao(
        codigo="lista_10",
        nome="Radar Afiado",
        descricao=("Adicione dez produtos " "distintos a Lista."),
        badge="lista-10",
        tipo_criterio="event_count",
        alvo=10,
        evento_tipo=("watchlist_produto_adicionado"),
    ),
    DefinicaoConquistaGamificacao(
        codigo="primeiro_alvo",
        nome="Preco na Mira",
        descricao=("Defina seu primeiro " "preco-alvo."),
        badge="preco-na-mira",
        tipo_criterio="event_count",
        alvo=1,
        evento_tipo=("watchlist_preco_alvo_definido"),
    ),
    DefinicaoConquistaGamificacao(
        codigo="setup_completo",
        nome="Setup Completo",
        descricao=("Conclua os marcos basicos " "de configuracao do Radar."),
        badge="setup-completo",
        tipo_criterio="all_events",
        alvo=4,
        eventos_requeridos=(
            "onboarding_conta_criada",
            "onboarding_dispositivo_vinculado",
            "onboarding_preferencias_definidas",
            "watchlist_produto_adicionado",
        ),
    ),
    DefinicaoConquistaGamificacao(
        codigo="nivel_5",
        nome="Veterano do Radar",
        descricao=("Alcance o nivel 5 " "de progressao."),
        badge="nivel-5",
        tipo_criterio="level",
        alvo=5,
    ),
)


def avaliar_conquistas(
    *,
    perfil: PerfilGamificacao,
    contagens_eventos: Mapping[str, int],
) -> tuple[EstadoConquistaGamificacao, ...]:
    estados: list[EstadoConquistaGamificacao] = []

    for definicao in CONQUISTAS_PRODUCAO_V1:
        if definicao.tipo_criterio == "event_count":
            atual = max(
                int(
                    contagens_eventos.get(
                        definicao.evento_tipo or "",
                        0,
                    )
                ),
                0,
            )

        elif definicao.tipo_criterio == "all_events":
            atual = sum(
                1
                for tipo in definicao.eventos_requeridos
                if int(
                    contagens_eventos.get(
                        tipo,
                        0,
                    )
                )
                > 0
            )

        else:
            atual = max(
                int(perfil.nivel),
                0,
            )

        estados.append(
            EstadoConquistaGamificacao(
                codigo=definicao.codigo,
                nome=definicao.nome,
                descricao=definicao.descricao,
                badge=definicao.badge,
                desbloqueada=(atual >= definicao.alvo),
                progresso_atual=min(
                    atual,
                    definicao.alvo,
                ),
                progresso_alvo=(definicao.alvo),
            )
        )

    return tuple(estados)
