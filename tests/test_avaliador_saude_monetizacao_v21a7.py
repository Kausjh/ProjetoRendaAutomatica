from __future__ import annotations

from services.avaliador_saude_monetizacao import (
    STATUS_CRITICO,
    STATUS_DADOS_INSUFICIENTES,
    STATUS_DEGRADADO,
    STATUS_SAUDAVEL,
    avaliar_saude_monetizacao,
)


def _contador(
    *,
    processamentos: int,
    transformados: int,
    bloqueios: int = 0,
    pass_through: int = 0,
    retries: int = 0,
    retry_minutos_total: int = 0,
):
    return {
        "processamentos": processamentos,
        "transformados": transformados,
        "bloqueios": bloqueios,
        "pass_through": pass_through,
        "retries": retries,
        "retry_minutos_total": retry_minutos_total,
    }


def _snapshot(
    *,
    processamentos: int,
    transformados: int,
    bloqueios: int = 0,
    pass_through: int = 0,
    retries: int = 0,
    retry_minutos_total: int = 0,
    por_origem=None,
    por_afiliador=None,
):
    return {
        "schema_version": 1,
        "iniciado_em": "2026-09-12T10:00:00-03:00",
        "atualizado_em": "2026-09-12T11:00:00-03:00",
        "eventos_total": (processamentos + retries),
        "processamentos_total": processamentos,
        "transformados_total": transformados,
        "bloqueios_total": bloqueios,
        "pass_through_total": pass_through,
        "retries_total": retries,
        "retry_minutos_total": retry_minutos_total,
        "por_origem": (por_origem if por_origem is not None else {}),
        "por_afiliador": (por_afiliador if por_afiliador is not None else {}),
        "por_dia": {},
        "ultimo_evento_em": "2026-09-12T11:00:00-03:00",
    }


def test_amostra_pequena_fica_dados_insuficientes():
    resultado = avaliar_saude_monetizacao(
        _snapshot(
            processamentos=9,
            transformados=9,
        )
    )

    assert resultado["status"] == STATUS_DADOS_INSUFICIENTES
    assert resultado["dados_validos"] is True
    assert resultado["amostra_suficiente"] is False


def test_amostra_suficiente_sem_sinal_ruim_fica_saudavel():
    resultado = avaliar_saude_monetizacao(
        _snapshot(
            processamentos=10,
            transformados=9,
            pass_through=1,
            retries=1,
            retry_minutos_total=15,
        )
    )

    assert resultado["status"] == STATUS_SAUDAVEL
    assert resultado["metricas"]["taxa_retry"] == 0.1


def test_bloqueio_degradado():
    resultado = avaliar_saude_monetizacao(
        _snapshot(
            processamentos=10,
            transformados=8,
            bloqueios=2,
        )
    )

    assert resultado["status"] == STATUS_DEGRADADO
    assert "taxa_bloqueio_degradada" in resultado["motivos"]


def test_bloqueio_critico():
    resultado = avaliar_saude_monetizacao(
        _snapshot(
            processamentos=10,
            transformados=6,
            bloqueios=4,
        )
    )

    assert resultado["status"] == STATUS_CRITICO
    assert "taxa_bloqueio_critica" in resultado["motivos"]


def test_retry_degradado():
    resultado = avaliar_saude_monetizacao(
        _snapshot(
            processamentos=10,
            transformados=10,
            retries=3,
            retry_minutos_total=45,
        )
    )

    assert resultado["status"] == STATUS_DEGRADADO
    assert "taxa_retry_degradada" in resultado["motivos"]


def test_retry_critico():
    resultado = avaliar_saude_monetizacao(
        _snapshot(
            processamentos=10,
            transformados=10,
            retries=6,
            retry_minutos_total=90,
        )
    )

    assert resultado["status"] == STATUS_CRITICO
    assert "taxa_retry_critica" in resultado["motivos"]


def test_segmento_critico_eleva_status_global():
    resultado = avaliar_saude_monetizacao(
        _snapshot(
            processamentos=100,
            transformados=98,
            bloqueios=2,
            por_origem={
                "mercadolivre": _contador(
                    processamentos=10,
                    transformados=6,
                    bloqueios=4,
                ),
                "outros": _contador(
                    processamentos=90,
                    transformados=90,
                ),
            },
        )
    )

    assert resultado["status"] == STATUS_CRITICO
    assert "origem:mercadolivre:critico" in resultado["motivos"]


def test_segmento_com_pouca_amostra_nao_rebaixa_global():
    resultado = avaliar_saude_monetizacao(
        _snapshot(
            processamentos=100,
            transformados=100,
            por_afiliador={
                "mercado_livre": _contador(
                    processamentos=3,
                    transformados=1,
                    bloqueios=2,
                ),
            },
        )
    )

    assert resultado["status"] == STATUS_SAUDAVEL
    assert resultado["por_afiliador"]["mercado_livre"]["status"] == STATUS_DADOS_INSUFICIENTES


def test_contadores_inconsistentes_nao_viram_falso_critico():
    resultado = avaliar_saude_monetizacao(
        _snapshot(
            processamentos=10,
            transformados=10,
        )
    )

    snapshot = _snapshot(
        processamentos=10,
        transformados=10,
    )
    snapshot["bloqueios_total"] = 1

    resultado = avaliar_saude_monetizacao(snapshot)

    assert resultado["status"] == STATUS_DADOS_INSUFICIENTES
    assert resultado["dados_validos"] is False
    assert "contador_invalido" in resultado["motivos"]


def test_avaliador_e_puro_e_nao_muta_snapshot():
    snapshot = _snapshot(
        processamentos=10,
        transformados=10,
    )
    antes = repr(snapshot)

    avaliar_saude_monetizacao(snapshot)

    assert repr(snapshot) == antes


# 63.8738, -149.7525
