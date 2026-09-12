from __future__ import annotations

from typing import Any

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.observador_monetizacao import (
    ObservadorMonetizacao,
)

SCHEMA_VERSION_ENFORCEMENT_SEGMENTADO = 1

ESCOPO_ORIGEM = "origem"
ESCOPO_AFILIADOR = "afiliador"
ESCOPOS_SUPORTADOS = {
    ESCOPO_ORIGEM,
    ESCOPO_AFILIADOR,
}

ACAO_SUSPENDER = "suspender"
ACAO_RETOMAR = "retomar"

RECOMENDACAO_ORIGEM = "considerar_isolamento_origem"
RECOMENDACAO_AFILIADOR = "considerar_suspensao_afiliador"

SEGMENTO_RETRY_MINUTOS = 15


class ErroEnforcementSegmentadoMonetizacao(RuntimeError):
    def __init__(
        self,
        *,
        escopo: str,
        alvo: str,
    ) -> None:
        self.escopo = escopo
        self.alvo = alvo

        super().__init__(
            "Publicacao bloqueada por enforcement "
            f"segmentado de monetizacao: "
            f"{escopo}={alvo}."
        )


def normalizar_escopo(
    escopo: str,
) -> str:
    valor = str(escopo).strip().casefold()

    if valor not in ESCOPOS_SUPORTADOS:
        raise ValueError("Escopo de enforcement segmentado " "nao suportado.")

    return valor


def normalizar_alvo(
    alvo: str,
) -> str:
    valor = str(alvo).strip().casefold()

    if not valor:
        raise ValueError("Alvo de enforcement segmentado " "nao pode ficar vazio.")

    if len(valor) > 160:
        raise ValueError("Alvo de enforcement segmentado " "excede o limite permitido.")

    return valor


def classificar_origem_monetizacao(
    link: str,
) -> str:
    # A taxonomia V21A12 reutiliza deliberadamente
    # a mesma fonte de verdade do observador V21A5.
    return ObservadorMonetizacao._classificar_origem(link)


def _recomendacao_esperada(
    escopo: str,
) -> str:
    if escopo == ESCOPO_ORIGEM:
        return RECOMENDACAO_ORIGEM

    return RECOMENDACAO_AFILIADOR


def _confirmacao_esperada(
    *,
    acao: str,
    escopo: str,
    alvo: str,
) -> str:
    return f"CONFIRMAR_{acao.upper()}:" f"{escopo}:{alvo}"


def _shadow_valido(
    shadow: dict[str, Any] | None,
) -> bool:
    if not isinstance(
        shadow,
        dict,
    ):
        return False

    return (
        shadow.get("schema_version") == 1
        and shadow.get("modo") == "shadow"
        and shadow.get("disponivel") is True
        and shadow.get("autoridade_operacional") is False
        and shadow.get("executa_automaticamente") is False
        and isinstance(
            shadow.get("recomendacoes"),
            list,
        )
    )


def _recomendacao_atual(
    *,
    shadow: dict[str, Any],
    escopo: str,
    alvo: str,
    recomendacao_id: str,
) -> dict[str, Any] | None:
    esperada = _recomendacao_esperada(escopo)

    for item in shadow.get(
        "recomendacoes",
        [],
    ):
        if not isinstance(
            item,
            dict,
        ):
            continue

        if item.get("id") != recomendacao_id:
            continue

        if (
            str(
                item.get(
                    "escopo",
                    "",
                )
            )
            .strip()
            .casefold()
            != escopo
        ):
            return None

        if (
            str(
                item.get(
                    "alvo",
                    "",
                )
            )
            .strip()
            .casefold()
            != alvo
        ):
            return None

        if item.get("acao_sugerida") != esperada:
            return None

        if item.get("severidade") != "critica":
            return None

        if item.get("executavel") is not False:
            return None

        if item.get("executada") is not False:
            return None

        if item.get("requer_confirmacao_humana") is not True:
            return None

        if item.get("autoridade_operacional") is not False:
            return None

        return item

    return None


def avaliar_enforcement_segmentado(
    *,
    shadow: dict[str, Any] | None,
    escopo: str,
    alvo: str,
    acao: str,
    confirmacao: str | None,
    recomendacao_id: str | None = None,
) -> dict[str, Any]:
    try:
        escopo_norm = normalizar_escopo(escopo)
        alvo_norm = normalizar_alvo(alvo)
    except ValueError as erro:
        return {
            "schema_version": (SCHEMA_VERSION_ENFORCEMENT_SEGMENTADO),
            "permitido": False,
            "manual": True,
            "automatico": False,
            "motivo": str(erro),
            "escopo": str(escopo).strip().casefold(),
            "alvo": str(alvo).strip().casefold(),
            "acao": str(acao).strip().casefold(),
            "recomendacao_id": None,
        }

    acao_norm = str(acao).strip().casefold()

    confirmacao_norm = str(confirmacao).strip() if confirmacao is not None else ""

    recomendacao_norm = str(recomendacao_id).strip() if recomendacao_id is not None else ""

    base = {
        "schema_version": (SCHEMA_VERSION_ENFORCEMENT_SEGMENTADO),
        "manual": True,
        "automatico": False,
        "requer_autenticacao_admin": True,
        "requer_confirmacao_explicita": True,
        "escopo": escopo_norm,
        "alvo": alvo_norm,
        "acao": acao_norm,
        "recomendacao_id": (recomendacao_norm or None),
    }

    if acao_norm not in {
        ACAO_SUSPENDER,
        ACAO_RETOMAR,
    }:
        return {
            **base,
            "permitido": False,
            "motivo": ("acao_nao_suportada"),
        }

    confirmacao_esperada = _confirmacao_esperada(
        acao=acao_norm,
        escopo=escopo_norm,
        alvo=alvo_norm,
    )

    if confirmacao_norm != confirmacao_esperada:
        return {
            **base,
            "permitido": False,
            "motivo": ("confirmacao_invalida"),
        }

    if acao_norm == ACAO_RETOMAR:
        return {
            **base,
            "permitido": True,
            "motivo": ("retomada_segmentada_confirmada"),
        }

    if escopo_norm == ESCOPO_ORIGEM and alvo_norm == "outro":
        return {
            **base,
            "permitido": False,
            "motivo": ("origem_outro_nao_pode_ser_suspensa"),
        }

    if escopo_norm == ESCOPO_AFILIADOR and alvo_norm in {
        "nenhum",
        "none",
    }:
        return {
            **base,
            "permitido": False,
            "motivo": ("afiliador_indefinido_nao_pode_ser_suspenso"),
        }

    if not recomendacao_norm:
        return {
            **base,
            "permitido": False,
            "motivo": ("recomendacao_id_obrigatoria"),
        }

    if not _shadow_valido(shadow):
        return {
            **base,
            "permitido": False,
            "motivo": ("shadow_atual_indisponivel"),
        }

    recomendacao = _recomendacao_atual(
        shadow=shadow,
        escopo=escopo_norm,
        alvo=alvo_norm,
        recomendacao_id=(recomendacao_norm),
    )

    if recomendacao is None:
        return {
            **base,
            "permitido": False,
            "motivo": ("recomendacao_segmentada_critica_nao_confere"),
        }

    return {
        **base,
        "permitido": True,
        "motivo": ("suspensao_segmentada_confirmada"),
    }


class EnforcementSegmentadoMonetizacao:
    def __init__(
        self,
        repositorio: ControleAdministrativoRepository,
    ) -> None:
        self.repositorio = repositorio

    def validar_origem(
        self,
        link_original: str,
    ) -> str:
        origem = classificar_origem_monetizacao(link_original)

        if self.repositorio.enforcement_segmento_monetizacao_ativo(
            ESCOPO_ORIGEM,
            origem,
        ):
            raise (
                ErroEnforcementSegmentadoMonetizacao(
                    escopo=ESCOPO_ORIGEM,
                    alvo=origem,
                )
            )

        return origem

    def validar_afiliador(
        self,
        afiliador: str,
    ) -> str:
        alvo = normalizar_alvo(afiliador)

        if self.repositorio.enforcement_segmento_monetizacao_ativo(
            ESCOPO_AFILIADOR,
            alvo,
        ):
            raise (
                ErroEnforcementSegmentadoMonetizacao(
                    escopo=ESCOPO_AFILIADOR,
                    alvo=alvo,
                )
            )

        return alvo
