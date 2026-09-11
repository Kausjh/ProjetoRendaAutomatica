from datetime import datetime, timedelta, timezone

import pytest

from services.scout.janela_learning_discovery_comercial_hunter import (
    criar_janela_learning_discovery_comercial_hunter,
)

TZ = timezone(timedelta(hours=-3))

AGORA = datetime(
    2026,
    9,
    11,
    19,
    0,
    0,
    tzinfo=TZ,
)


def _relatorio(
    data_hora,
    fonte="KabumScraper",
):
    return {
        "data_hora": data_hora,
        "commercial_discovery_outcome": {
            "schema_version": 1,
            "status": "observado",
            "alvos_aplicados": 1,
            "fontes": [
                {
                    "fonte_hunter": fonte,
                    "limite_solicitado": 10,
                    "quantidade_coletada": 10,
                    "quantidade_novas": 5,
                    "quantidade_duplicadas": 5,
                    "elegiveis_atribuidas": 3,
                    "selecionadas_fila_atribuidas": 1,
                    "sucesso": True,
                    "erro": None,
                }
            ],
        },
    }


def _publicacao(
    publicado_em,
    fonte="KabumScraper",
):
    return {
        "link": ("https://exemplo/item"),
        "publicado_em": publicado_em,
        "proveniencia_discovery_comercial": {
            "schema_version": 1,
            "origem": ("commercial_discovery_hunter"),
            "granularidade": ("fonte_hunter"),
            "fontes_hunter_guiadas": [fonte],
        },
    }


def test_sem_evidencias_na_janela():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        agora=AGORA,
    )

    assert resultado["status"] == "sem_evidencias_na_janela"

    assert resultado["tem_evidencia_madura"] is False


def test_relatorio_com_dois_dias_e_maduro():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio(AGORA - timedelta(days=2))],
        agora=AGORA,
    )

    assert resultado["relatorios"]["maduros"] == 1

    assert resultado["status"] == "evidencia_madura_disponivel"


def test_relatorio_com_duas_horas_e_recente():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio(AGORA - timedelta(hours=2))],
        agora=AGORA,
    )

    assert resultado["relatorios"]["recentes"] == 1

    assert resultado["status"] == "aguardando_maturacao"


def test_limite_de_24h_ja_e_maduro():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio(AGORA - timedelta(hours=24))],
        agora=AGORA,
    )

    assert resultado["relatorios"]["maduros"] == 1


def test_evento_mais_antigo_que_sete_dias_fica_fora():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio(AGORA - timedelta(days=8))],
        agora=AGORA,
    )

    assert resultado["relatorios"]["fora_janela"] == 1


def test_evento_futuro_e_ignorado():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio(AGORA + timedelta(hours=1))],
        agora=AGORA,
    )

    assert resultado["relatorios"]["futuros"] == 1


def test_data_invalida_e_contabilizada():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio("nao-e-data")],
        agora=AGORA,
    )

    assert resultado["relatorios"]["invalidos"] == 1


def test_publicacao_madura_vai_para_dataset_maduro():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        historico_publicacoes=[_publicacao(AGORA - timedelta(days=2))],
        agora=AGORA,
    )

    assert resultado["publicacoes"]["maduras"] == 1

    assert resultado["dataset_maduro"]["publicacoes_atribuidas_discovery"] == 1


def test_publicacao_recente_nao_contamina_dataset_maduro():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        historico_publicacoes=[_publicacao(AGORA - timedelta(hours=2))],
        agora=AGORA,
    )

    assert resultado["publicacoes"]["recentes"] == 1

    assert resultado["dataset_maduro"]["publicacoes_atribuidas_discovery"] == 0

    assert resultado["dataset_recente"]["publicacoes_atribuidas_discovery"] == 1


def test_dataset_maduro_agrega_apenas_execucao_madura():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[
            _relatorio(AGORA - timedelta(days=2)),
            _relatorio(AGORA - timedelta(hours=2)),
        ],
        agora=AGORA,
    )

    fontes = resultado["dataset_maduro"]["fontes"]

    assert len(fontes) == 1

    assert fontes[0]["execucoes_guiadas"] == 1


def test_data_hora_naive_do_relatorio_e_tolerada():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio("2026-09-09 19:00:00")],
        agora=AGORA,
    )

    assert resultado["relatorios"]["maduros"] == 1


def test_iso_com_offset_e_normalizado():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        historico_publicacoes=[_publicacao("2026-09-09T22:00:00+00:00")],
        agora=AGORA,
    )

    assert resultado["publicacoes"]["maduras"] == 1


def test_janela_customizavel():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio(AGORA - timedelta(hours=20))],
        agora=AGORA,
        dias_janela=3,
        horas_maturacao=12,
    )

    assert resultado["relatorios"]["maduros"] == 1


@pytest.mark.parametrize(
    (
        "dias",
        "horas",
    ),
    [
        (
            0,
            24,
        ),
        (
            -1,
            24,
        ),
        (
            7,
            -1,
        ),
        (
            1,
            24,
        ),
        (
            1,
            48,
        ),
    ],
)
def test_parametros_temporais_invalidos(
    dias,
    horas,
):
    with pytest.raises(ValueError):
        criar_janela_learning_discovery_comercial_hunter(
            agora=AGORA,
            dias_janela=dias,
            horas_maturacao=horas,
        )


def test_nao_calcula_score_nem_taxa_publicacao():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[_relatorio(AGORA - timedelta(days=2))],
        historico_publicacoes=[_publicacao(AGORA - timedelta(days=2))],
        agora=AGORA,
    )

    assert resultado["score_learning_calculado"] is False

    assert resultado["taxa_publicacao_nao_calculada"] is True

    assert resultado["influencia_priorizacao"] is False


def test_recente_e_maduro_ficam_separados():
    resultado = criar_janela_learning_discovery_comercial_hunter(
        relatorios_execucao=[
            _relatorio(AGORA - timedelta(days=2)),
            _relatorio(AGORA - timedelta(hours=3)),
        ],
        historico_publicacoes=[
            _publicacao(AGORA - timedelta(days=2)),
            _publicacao(AGORA - timedelta(hours=3)),
        ],
        agora=AGORA,
    )

    assert resultado["relatorios"]["maduros"] == 1

    assert resultado["relatorios"]["recentes"] == 1

    assert resultado["publicacoes"]["maduras"] == 1

    assert resultado["publicacoes"]["recentes"] == 1
