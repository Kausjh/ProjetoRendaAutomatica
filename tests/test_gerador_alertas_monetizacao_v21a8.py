from __future__ import annotations

from copy import deepcopy

from services.gerador_alertas_monetizacao import (
    gerar_alertas_monetizacao,
)


def _avaliacao(
    *,
    status: str,
    motivos=None,
    dados_validos: bool = True,
    amostra_suficiente: bool = True,
):
    return {
        "status": status,
        "dados_validos": dados_validos,
        "amostra_suficiente": amostra_suficiente,
        "metricas": {},
        "motivos": (motivos if motivos is not None else []),
    }


def _saude(
    *,
    status: str = "saudavel",
    motivos=None,
    dados_validos: bool = True,
    amostra_suficiente: bool = True,
    por_origem=None,
    por_afiliador=None,
):
    return {
        "schema_version": 1,
        "status": status,
        "dados_validos": dados_validos,
        "amostra_suficiente": amostra_suficiente,
        "motivos": (motivos if motivos is not None else []),
        "metricas": {},
        "por_origem": (por_origem if por_origem is not None else {}),
        "por_afiliador": (por_afiliador if por_afiliador is not None else {}),
        "limiares": {},
    }


def test_saudavel_nao_gera_alerta():
    resultado = gerar_alertas_monetizacao(_saude())

    assert resultado["disponivel"] is True
    assert resultado["alertas_total"] == 0
    assert resultado["alertas"] == []


def test_amostra_insuficiente_valida_nao_gera_ruido():
    resultado = gerar_alertas_monetizacao(
        _saude(
            status="dados_insuficientes",
            motivos=[
                "amostra_insuficiente",
            ],
            amostra_suficiente=False,
        )
    )

    assert resultado["alertas_total"] == 0


def test_dados_invalidos_geram_aviso_de_qualidade():
    resultado = gerar_alertas_monetizacao(
        _saude(
            status="dados_insuficientes",
            motivos=[
                "contador_invalido",
            ],
            dados_validos=False,
            amostra_suficiente=False,
        )
    )

    assert resultado["alertas_total"] == 1

    alerta = resultado["alertas"][0]

    assert alerta["codigo"] == "dados_invalidos"
    assert alerta["severidade"] == "aviso"
    assert alerta["escopo"] == "global"


def test_degradado_global_gera_aviso():
    resultado = gerar_alertas_monetizacao(
        _saude(
            status="degradado",
            motivos=[
                "taxa_bloqueio_degradada",
            ],
        )
    )

    assert resultado["alertas_total"] == 1
    assert resultado["avisos_total"] == 1
    assert resultado["criticos_total"] == 0

    alerta = resultado["alertas"][0]

    assert alerta["codigo"] == "taxa_bloqueio_degradada"
    assert alerta["severidade"] == "aviso"


def test_critico_global_gera_alerta_critico():
    resultado = gerar_alertas_monetizacao(
        _saude(
            status="critico",
            motivos=[
                "taxa_retry_critica",
            ],
        )
    )

    assert resultado["alertas_total"] == 1
    assert resultado["criticos_total"] == 1
    assert resultado["alertas"][0]["severidade"] == "critica"


def test_segmento_critico_gera_alerta_sem_falso_global():
    resultado = gerar_alertas_monetizacao(
        _saude(
            status="critico",
            motivos=[
                "origem:mercadolivre:critico",
            ],
            por_origem={
                "mercadolivre": _avaliacao(
                    status="critico",
                    motivos=[
                        "taxa_bloqueio_critica",
                    ],
                ),
            },
        )
    )

    assert resultado["alertas_total"] == 1

    alerta = resultado["alertas"][0]

    assert alerta["escopo"] == "origem"
    assert alerta["alvo"] == "mercadolivre"
    assert alerta["codigo"] == "taxa_bloqueio_critica"


def test_afiliador_degradado_gera_alerta():
    resultado = gerar_alertas_monetizacao(
        _saude(
            status="degradado",
            motivos=[
                "afiliador:awin:degradado",
            ],
            por_afiliador={
                "awin": _avaliacao(
                    status="degradado",
                    motivos=[
                        "taxa_retry_degradada",
                    ],
                ),
            },
        )
    )

    assert resultado["alertas_total"] == 1

    alerta = resultado["alertas"][0]

    assert alerta["escopo"] == "afiliador"
    assert alerta["alvo"] == "awin"


def test_segmento_sem_amostra_suficiente_nao_gera_alerta():
    resultado = gerar_alertas_monetizacao(
        _saude(
            status="saudavel",
            por_afiliador={
                "novo": _avaliacao(
                    status="dados_insuficientes",
                    motivos=[
                        "amostra_insuficiente",
                    ],
                    amostra_suficiente=False,
                ),
            },
        )
    )

    assert resultado["alertas_total"] == 0


def test_alertas_sao_deterministicos():
    saude = _saude(
        status="critico",
        motivos=[
            "taxa_retry_critica",
            "taxa_bloqueio_critica",
        ],
    )

    primeiro = gerar_alertas_monetizacao(saude)
    segundo = gerar_alertas_monetizacao(saude)

    assert primeiro == segundo


def test_gerador_nao_muta_saude():
    saude = _saude(
        status="degradado",
        motivos=[
            "taxa_retry_degradada",
        ],
    )

    antes = deepcopy(saude)

    gerar_alertas_monetizacao(saude)

    assert saude == antes


def test_schema_incompativel_fica_indisponivel():
    saude = _saude()
    saude["schema_version"] = 999

    resultado = gerar_alertas_monetizacao(saude)

    assert resultado["disponivel"] is False
    assert resultado["alertas_total"] == 0


# 63.8738, -149.7525
