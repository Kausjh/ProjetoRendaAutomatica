# 63.8738, -149.7525

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from models.oferta import Oferta
from models.resultado_hunter_v2 import ResultadoHunterV2

SCHEMA_VERSION = 1
GRANULARIDADE = "fonte_hunter"


def criar_feedback_outcome_discovery_comercial_hunter(
    *,
    observabilidade: Mapping[str, Any],
    resultado_hunter: ResultadoHunterV2 | None,
    ofertas_elegiveis: Iterable[Oferta] = (),
    ofertas_selecionadas_fila: Iterable[Oferta] = (),
) -> dict[str, Any]:
    """
    Mede o resultado de fontes guiadas pelo Commercial Discovery.

    Esta camada e estritamente observacional.

    O Hunter V2 preserva a origem por fonte em CandidatoHunterV2.fontes,
    mas nao preserva qual termo de busca individual originou cada oferta.
    Por isso esta versao NAO atribui resultado a um alvo/termo especifico.
    """

    fontes_guiadas = _fontes_guiadas(observabilidade)

    if not fontes_guiadas:
        return _resultado_base(
            status="sem_alvos_aplicados",
            motivo_status=("nenhum_alvo_discovery_aplicado_no_runtime"),
            fontes=[],
        )

    if resultado_hunter is None:
        return _resultado_base(
            status="sem_resultado_hunter",
            motivo_status=("resultado_hunter_indisponivel_para_feedback"),
            fontes=[
                _fonte_sem_resultado(
                    fonte=fonte,
                    alvos_aplicados=quantidade,
                )
                for fonte, quantidade in fontes_guiadas
            ],
        )

    fontes_hunter = {item.fonte: item for item in resultado_hunter.fontes}

    fontes_por_link = _fontes_por_link(resultado_hunter)

    elegiveis = tuple(ofertas_elegiveis)

    selecionadas = tuple(ofertas_selecionadas_fila)

    resultados: list[dict[str, Any]] = []

    fontes_ausentes = 0

    for fonte, quantidade_alvos in fontes_guiadas:

        resultado_fonte = fontes_hunter.get(fonte)

        if resultado_fonte is None:
            fontes_ausentes += 1

            resultados.append(
                _fonte_sem_resultado(
                    fonte=fonte,
                    alvos_aplicados=(quantidade_alvos),
                )
            )

            continue

        elegiveis_atribuidas = _contar_atribuidas(
            ofertas=elegiveis,
            fonte=fonte,
            fontes_por_link=(fontes_por_link),
        )

        selecionadas_atribuidas = _contar_atribuidas(
            ofertas=selecionadas,
            fonte=fonte,
            fontes_por_link=(fontes_por_link),
        )

        novas = resultado_fonte.quantidade_novas

        resultados.append(
            {
                "fonte_hunter": fonte,
                "alvos_aplicados": (quantidade_alvos),
                "status": "observado",
                "limite_solicitado": (resultado_fonte.limite_solicitado),
                "quantidade_coletada": (resultado_fonte.quantidade_coletada),
                "quantidade_novas": novas,
                "quantidade_duplicadas": (resultado_fonte.quantidade_duplicadas),
                "sucesso": (resultado_fonte.sucesso),
                "erro": (resultado_fonte.erro),
                "elegiveis_atribuidas": (elegiveis_atribuidas),
                "selecionadas_fila_atribuidas": (selecionadas_atribuidas),
                "taxa_elegibilidade_percentual": (
                    _percentual(
                        elegiveis_atribuidas,
                        novas,
                    )
                ),
                "taxa_selecao_fila_percentual": (
                    _percentual(
                        selecionadas_atribuidas,
                        novas,
                    )
                ),
            }
        )

    if fontes_ausentes == 0:
        status = "observado"
        motivo_status = "todas_fontes_guiadas_observadas"

    elif fontes_ausentes < len(fontes_guiadas):
        status = "observado_parcialmente"
        motivo_status = "parte_das_fontes_guiadas_" "ausente_no_resultado_hunter"

    else:
        status = "nao_observado"
        motivo_status = "fontes_guiadas_ausentes_" "no_resultado_hunter"

    return _resultado_base(
        status=status,
        motivo_status=motivo_status,
        fontes=resultados,
    )


def _resultado_base(
    *,
    status: str,
    motivo_status: str,
    fontes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": (SCHEMA_VERSION),
        "status": status,
        "motivo_status": (motivo_status),
        "granularidade": (GRANULARIDADE),
        "atribuicao_alvo_individual": (False),
        "motivo_granularidade": ("hunter_preserva_origem_por_" "fonte_mas_nao_por_termo_de_busca"),
        "fontes_total": len(fontes),
        "fontes": fontes,
    }


def _fontes_guiadas(
    observabilidade: Mapping[
        str,
        Any,
    ],
) -> tuple[
    tuple[str, int],
    ...,
]:
    contagem: dict[
        str,
        int,
    ] = {}

    alvos = observabilidade.get(
        "alvos",
        (),
    )

    if not isinstance(
        alvos,
        (list, tuple),
    ):
        return ()

    for alvo in alvos:

        if not isinstance(
            alvo,
            Mapping,
        ):
            continue

        if not bool(alvo.get("aplicado")):
            continue

        fonte = str(
            alvo.get(
                "fonte_hunter",
                "",
            )
            or ""
        ).strip()

        if not fonte:
            continue

        contagem[fonte] = (
            contagem.get(
                fonte,
                0,
            )
            + 1
        )

    return tuple(
        sorted(
            contagem.items(),
            key=lambda item: (item[0]),
        )
    )


def _fontes_por_link(
    resultado: ResultadoHunterV2,
) -> dict[
    str,
    set[str],
]:
    mapa: dict[
        str,
        set[str],
    ] = {}

    for candidato in resultado.candidatos:

        link = _link(candidato.oferta)

        if not link:
            continue

        fontes = {str(fonte).strip() for fonte in candidato.fontes if str(fonte).strip()}

        if not fontes:
            continue

        mapa.setdefault(
            link,
            set(),
        ).update(fontes)

    return mapa


def _contar_atribuidas(
    *,
    ofertas: Iterable[Oferta],
    fonte: str,
    fontes_por_link: Mapping[
        str,
        set[str],
    ],
) -> int:
    vistos: set[str] = set()

    for oferta in ofertas:

        link = _link(oferta)

        if not link or link in vistos:
            continue

        fontes = fontes_por_link.get(
            link,
            set(),
        )

        if fonte not in fontes:
            continue

        vistos.add(link)

    return len(vistos)


def _fonte_sem_resultado(
    *,
    fonte: str,
    alvos_aplicados: int,
) -> dict[str, Any]:
    return {
        "fonte_hunter": fonte,
        "alvos_aplicados": (alvos_aplicados),
        "status": ("fonte_ausente_resultado_hunter"),
        "limite_solicitado": None,
        "quantidade_coletada": None,
        "quantidade_novas": None,
        "quantidade_duplicadas": None,
        "sucesso": None,
        "erro": None,
        "elegiveis_atribuidas": (None),
        "selecionadas_fila_atribuidas": (None),
        "taxa_elegibilidade_percentual": (None),
        "taxa_selecao_fila_percentual": (None),
    }


def _link(
    oferta: Oferta,
) -> str:
    return str(oferta.link or "").strip()


def _percentual(
    quantidade: int,
    total: int,
) -> float:
    if total <= 0:
        return 0.0

    return round(
        (quantidade / total) * 100,
        2,
    )
