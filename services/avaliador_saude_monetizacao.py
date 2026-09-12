from __future__ import annotations

from typing import Any

STATUS_DADOS_INSUFICIENTES = "dados_insuficientes"
STATUS_SAUDAVEL = "saudavel"
STATUS_DEGRADADO = "degradado"
STATUS_CRITICO = "critico"

AMOSTRA_MINIMA = 10

LIMITE_BLOQUEIO_DEGRADADO = 0.15
LIMITE_BLOQUEIO_CRITICO = 0.35

LIMITE_RETRY_DEGRADADO = 0.25
LIMITE_RETRY_CRITICO = 0.60

SCHEMA_VERSION_SAUDE_MONETIZACAO = 1


def _inteiro_nao_negativo(
    dados: dict[str, Any],
    campo: str,
) -> int | None:
    valor = dados.get(campo)

    if isinstance(valor, bool):
        return None

    if not isinstance(valor, int):
        return None

    if valor < 0:
        return None

    return valor


def _normalizar_contador(
    dados: dict[str, Any],
) -> dict[str, int] | None:
    campos = (
        "processamentos",
        "transformados",
        "bloqueios",
        "pass_through",
        "retries",
        "retry_minutos_total",
    )

    contador: dict[str, int] = {}

    for campo in campos:
        valor = _inteiro_nao_negativo(
            dados,
            campo,
        )

        if valor is None:
            return None

        contador[campo] = valor

    resultados = contador["transformados"] + contador["bloqueios"] + contador["pass_through"]

    if resultados != contador["processamentos"]:
        return None

    return contador


def _metricas(
    contador: dict[str, int],
) -> dict[str, int | float]:
    processamentos = contador["processamentos"]
    retries = contador["retries"]

    if processamentos > 0:
        taxa_transformacao = contador["transformados"] / processamentos
        taxa_bloqueio = contador["bloqueios"] / processamentos
        taxa_pass_through = contador["pass_through"] / processamentos
        taxa_retry = retries / processamentos
    else:
        taxa_transformacao = 0.0
        taxa_bloqueio = 0.0
        taxa_pass_through = 0.0
        taxa_retry = 0.0

    if retries > 0:
        retry_minutos_medio = contador["retry_minutos_total"] / retries
    else:
        retry_minutos_medio = 0.0

    return {
        **contador,
        "taxa_transformacao": round(
            taxa_transformacao,
            4,
        ),
        "taxa_bloqueio": round(
            taxa_bloqueio,
            4,
        ),
        "taxa_pass_through": round(
            taxa_pass_through,
            4,
        ),
        "taxa_retry": round(
            taxa_retry,
            4,
        ),
        "retry_minutos_medio": round(
            retry_minutos_medio,
            2,
        ),
    }


def _avaliar_contador(
    dados: dict[str, Any],
) -> dict[str, Any]:
    contador = _normalizar_contador(
        dados,
    )

    if contador is None:
        return {
            "status": STATUS_DADOS_INSUFICIENTES,
            "dados_validos": False,
            "amostra_suficiente": False,
            "metricas": None,
            "motivos": [
                "contador_invalido",
            ],
        }

    metricas = _metricas(
        contador,
    )

    if contador["processamentos"] < AMOSTRA_MINIMA:
        return {
            "status": STATUS_DADOS_INSUFICIENTES,
            "dados_validos": True,
            "amostra_suficiente": False,
            "metricas": metricas,
            "motivos": [
                "amostra_insuficiente",
            ],
        }

    taxa_bloqueio = float(metricas["taxa_bloqueio"])
    taxa_retry = float(metricas["taxa_retry"])

    motivos_criticos: list[str] = []

    if taxa_bloqueio >= LIMITE_BLOQUEIO_CRITICO:
        motivos_criticos.append("taxa_bloqueio_critica")

    if taxa_retry >= LIMITE_RETRY_CRITICO:
        motivos_criticos.append("taxa_retry_critica")

    if motivos_criticos:
        return {
            "status": STATUS_CRITICO,
            "dados_validos": True,
            "amostra_suficiente": True,
            "metricas": metricas,
            "motivos": motivos_criticos,
        }

    motivos_degradados: list[str] = []

    if taxa_bloqueio >= LIMITE_BLOQUEIO_DEGRADADO:
        motivos_degradados.append("taxa_bloqueio_degradada")

    if taxa_retry >= LIMITE_RETRY_DEGRADADO:
        motivos_degradados.append("taxa_retry_degradada")

    if motivos_degradados:
        return {
            "status": STATUS_DEGRADADO,
            "dados_validos": True,
            "amostra_suficiente": True,
            "metricas": metricas,
            "motivos": motivos_degradados,
        }

    return {
        "status": STATUS_SAUDAVEL,
        "dados_validos": True,
        "amostra_suficiente": True,
        "metricas": metricas,
        "motivos": [],
    }


def _avaliar_segmentos(
    segmentos: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    resultado: dict[
        str,
        dict[str, Any],
    ] = {}

    for nome, dados in sorted(
        segmentos.items(),
        key=lambda item: str(item[0]),
    ):
        chave = str(nome)

        if not isinstance(dados, dict):
            resultado[chave] = {
                "status": STATUS_DADOS_INSUFICIENTES,
                "dados_validos": False,
                "amostra_suficiente": False,
                "metricas": None,
                "motivos": [
                    "contador_invalido",
                ],
            }
            continue

        resultado[chave] = _avaliar_contador(
            dados,
        )

    return resultado


def _ranking(
    status: str,
) -> int:
    return {
        STATUS_DADOS_INSUFICIENTES: 0,
        STATUS_SAUDAVEL: 1,
        STATUS_DEGRADADO: 2,
        STATUS_CRITICO: 3,
    }.get(
        status,
        0,
    )


def avaliar_saude_monetizacao(
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {
            "schema_version": SCHEMA_VERSION_SAUDE_MONETIZACAO,
            "status": STATUS_DADOS_INSUFICIENTES,
            "dados_validos": False,
            "amostra_suficiente": False,
            "motivos": [
                "snapshot_invalido",
            ],
            "metricas": None,
            "por_origem": {},
            "por_afiliador": {},
            "limiares": _limiares(),
        }

    if snapshot.get("schema_version") != 1:
        return {
            "schema_version": SCHEMA_VERSION_SAUDE_MONETIZACAO,
            "status": STATUS_DADOS_INSUFICIENTES,
            "dados_validos": False,
            "amostra_suficiente": False,
            "motivos": [
                "schema_snapshot_incompativel",
            ],
            "metricas": None,
            "por_origem": {},
            "por_afiliador": {},
            "limiares": _limiares(),
        }

    por_origem = snapshot.get(
        "por_origem",
    )
    por_afiliador = snapshot.get(
        "por_afiliador",
    )

    if not isinstance(
        por_origem,
        dict,
    ) or not isinstance(
        por_afiliador,
        dict,
    ):
        return {
            "schema_version": SCHEMA_VERSION_SAUDE_MONETIZACAO,
            "status": STATUS_DADOS_INSUFICIENTES,
            "dados_validos": False,
            "amostra_suficiente": False,
            "motivos": [
                "segmentos_invalidos",
            ],
            "metricas": None,
            "por_origem": {},
            "por_afiliador": {},
            "limiares": _limiares(),
        }

    global_bruto = {
        "processamentos": snapshot.get("processamentos_total"),
        "transformados": snapshot.get("transformados_total"),
        "bloqueios": snapshot.get("bloqueios_total"),
        "pass_through": snapshot.get("pass_through_total"),
        "retries": snapshot.get("retries_total"),
        "retry_minutos_total": snapshot.get("retry_minutos_total"),
    }

    global_resultado = _avaliar_contador(
        global_bruto,
    )

    origens = _avaliar_segmentos(
        por_origem,
    )
    afiliadores = _avaliar_segmentos(
        por_afiliador,
    )

    segmentos_invalidos = any(
        not item["dados_validos"] for item in (list(origens.values()) + list(afiliadores.values()))
    )

    motivos = list(global_resultado["motivos"])

    if not global_resultado["dados_validos"] or segmentos_invalidos:
        if segmentos_invalidos:
            motivos.append("segmento_invalido")

        return {
            "schema_version": SCHEMA_VERSION_SAUDE_MONETIZACAO,
            "status": STATUS_DADOS_INSUFICIENTES,
            "dados_validos": False,
            "amostra_suficiente": bool(global_resultado["amostra_suficiente"]),
            "motivos": sorted(set(motivos)),
            "metricas": global_resultado["metricas"],
            "por_origem": origens,
            "por_afiliador": afiliadores,
            "limiares": _limiares(),
        }

    status_final = str(global_resultado["status"])

    if status_final != STATUS_DADOS_INSUFICIENTES:
        for categoria, segmentos in (
            ("origem", origens),
            ("afiliador", afiliadores),
        ):
            for nome, avaliacao in segmentos.items():
                status_segmento = str(avaliacao["status"])

                if status_segmento == STATUS_DADOS_INSUFICIENTES:
                    continue

                if _ranking(status_segmento) > _ranking(status_final):
                    status_final = status_segmento

                if status_segmento in (
                    STATUS_DEGRADADO,
                    STATUS_CRITICO,
                ):
                    motivos.append(f"{categoria}:{nome}:{status_segmento}")

    return {
        "schema_version": SCHEMA_VERSION_SAUDE_MONETIZACAO,
        "status": status_final,
        "dados_validos": True,
        "amostra_suficiente": bool(global_resultado["amostra_suficiente"]),
        "motivos": sorted(set(motivos)),
        "metricas": global_resultado["metricas"],
        "por_origem": origens,
        "por_afiliador": afiliadores,
        "limiares": _limiares(),
    }


def _limiares() -> dict[str, int | float]:
    return {
        "amostra_minima": AMOSTRA_MINIMA,
        "bloqueio_degradado": LIMITE_BLOQUEIO_DEGRADADO,
        "bloqueio_critico": LIMITE_BLOQUEIO_CRITICO,
        "retry_degradado": LIMITE_RETRY_DEGRADADO,
        "retry_critico": LIMITE_RETRY_CRITICO,
    }
