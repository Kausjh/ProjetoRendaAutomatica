from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

# 63.8738, -149.7525

SCHEMA_VERSION = 1
ORIGEM = "commercial_discovery_hunter"
GRANULARIDADE = "fonte_hunter"
MOTIVO_GRANULARIDADE = "hunter_preserva_origem_por_fonte_mas_nao_por_termo_de_busca"


def criar_proveniencias_publicacao_discovery_comercial_hunter(
    *,
    observabilidade: Mapping[str, Any],
    resultado_hunter: Any,
    ofertas_selecionadas_fila: Iterable[Any] = (),
) -> dict[str, dict[str, Any]]:
    """Mapeia ofertas da fila para fontes Hunter guiadas.

    O resultado e indexado pelo link da oferta.

    Esta camada nao altera score, elegibilidade, fila ou publicacao.
    Ela apenas preserva a origem observavel que ja existe no Hunter.

    A atribuicao deliberadamente para em ``fonte_hunter`` porque o
    Hunter preserva a origem por fonte, mas nao o termo individual que
    produziu cada candidato.
    """

    fontes_guiadas = _fontes_hunter_guiadas(observabilidade)

    if not fontes_guiadas or resultado_hunter is None:
        return {}

    links_selecionados = {
        link for oferta in ofertas_selecionadas_fila if (link := _link_oferta(oferta))
    }

    if not links_selecionados:
        return {}

    candidatos = (
        getattr(
            resultado_hunter,
            "candidatos",
            (),
        )
        or ()
    )

    proveniencias: dict[
        str,
        dict[str, Any],
    ] = {}

    for candidato in candidatos:
        oferta = getattr(
            candidato,
            "oferta",
            None,
        )

        link = _link_oferta(oferta)

        if not link or link not in links_selecionados:
            continue

        fontes_candidato = {
            fonte_normalizada
            for fonte in (
                getattr(
                    candidato,
                    "fontes",
                    (),
                )
                or ()
            )
            if (fonte_normalizada := _normalizar_fonte(fonte))
        }

        fontes_atribuidas = sorted(fontes_candidato & fontes_guiadas)

        if not fontes_atribuidas:
            continue

        proveniencias[link] = {
            "schema_version": SCHEMA_VERSION,
            "origem": ORIGEM,
            "granularidade": GRANULARIDADE,
            "atribuicao_alvo_individual": False,
            "motivo_granularidade": (MOTIVO_GRANULARIDADE),
            "fontes_hunter_guiadas": (fontes_atribuidas),
        }

    return proveniencias


def _fontes_hunter_guiadas(
    observabilidade: Mapping[str, Any],
) -> set[str]:
    fontes: set[str] = set()

    alvos = (
        observabilidade.get(
            "alvos",
            (),
        )
        or ()
    )

    for alvo in alvos:
        if not isinstance(
            alvo,
            Mapping,
        ):
            continue

        if alvo.get("aplicado") is not True:
            continue

        fonte = _normalizar_fonte(alvo.get("fonte_hunter"))

        if fonte:
            fontes.add(fonte)

    return fontes


def _normalizar_fonte(
    fonte: Any,
) -> str:
    return str(fonte or "").strip()


def _link_oferta(
    oferta: Any,
) -> str:
    if oferta is None:
        return ""

    return str(
        getattr(
            oferta,
            "link",
            "",
        )
        or ""
    ).strip()
