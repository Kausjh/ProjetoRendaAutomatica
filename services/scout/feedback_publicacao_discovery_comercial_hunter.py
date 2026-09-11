from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

# 63.8738, -149.7525

SCHEMA_VERSION = 1
ORIGEM = "commercial_discovery_hunter"
GRANULARIDADE = "fonte_hunter"


def criar_feedback_publicacao_discovery_comercial_hunter(
    *,
    historico_publicacoes: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Agrega publicacoes reais atribuiveis ao Commercial Discovery.

    Esta camada e exclusivamente observacional.

    Uma publicacao multifonte e contada uma unica vez no total de
    eventos atribu?dos, mas recebe credito em cada fonte Hunter que
    efetivamente participou da origem daquele candidato.

    Por isso, a soma de ``publicacoes_atribuidas`` por fonte pode ser
    maior que ``publicacoes_atribuidas_discovery``.
    """

    registros = [
        registro
        for registro in historico_publicacoes
        if isinstance(
            registro,
            Mapping,
        )
    ]

    contagem_fontes: Counter[str] = Counter()

    publicacoes_atribuidas = 0
    publicacoes_sem_proveniencia = 0
    eventos_multifonte = 0

    for registro in registros:
        proveniencia = registro.get("proveniencia_discovery_comercial")

        fontes = _fontes_atribuiveis(proveniencia)

        if not fontes:
            publicacoes_sem_proveniencia += 1
            continue

        publicacoes_atribuidas += 1

        if len(fontes) > 1:
            eventos_multifonte += 1

        for fonte in fontes:
            contagem_fontes[fonte] += 1

    fontes_resultado = [
        {
            "fonte_hunter": fonte,
            "publicacoes_atribuidas": quantidade,
        }
        for fonte, quantidade in sorted(contagem_fontes.items())
    ]

    status: str

    if not registros:
        status = "sem_publicacoes_observadas"
    elif not publicacoes_atribuidas:
        status = "sem_publicacoes_atribuidas"
    else:
        status = "observado"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "granularidade": GRANULARIDADE,
        "atribuicao_alvo_individual": False,
        "publicacoes_observadas": len(registros),
        "publicacoes_atribuidas_discovery": (publicacoes_atribuidas),
        "publicacoes_sem_proveniencia_discovery": (publicacoes_sem_proveniencia),
        "eventos_multifonte": eventos_multifonte,
        "fontes_total": len(fontes_resultado),
        "soma_por_fonte_pode_exceder_total": True,
        "fontes": fontes_resultado,
    }


def _fontes_atribuiveis(
    proveniencia: Any,
) -> tuple[str, ...]:
    if not isinstance(
        proveniencia,
        Mapping,
    ):
        return ()

    if proveniencia.get("origem") != ORIGEM:
        return ()

    if proveniencia.get("granularidade") != GRANULARIDADE:
        return ()

    fontes_brutas = proveniencia.get("fontes_hunter_guiadas")

    if not isinstance(
        fontes_brutas,
        (
            list,
            tuple,
            set,
            frozenset,
        ),
    ):
        return ()

    fontes = {
        fonte_normalizada
        for fonte in fontes_brutas
        if (fonte_normalizada := str(fonte or "").strip())
    }

    return tuple(sorted(fontes))
