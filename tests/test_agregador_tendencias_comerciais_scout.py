from datetime import UTC, datetime, timedelta

import pytest

from models.perfil_comercial_scout import (
    PerfilComercialScout,
)
from models.tendencia_comercial_scout import (
    ObservacaoComercialScout,
)
from services.scout.agregador_tendencias_comerciais_scout import (
    AgregadorTendenciasComerciaisScout,
)

AGORA = datetime(
    2026,
    9,
    10,
    18,
    0,
    tzinfo=UTC,
)


def criar_perfil(
    id_externo,
    *,
    marketplace=None,
    parceiro_id=None,
    parceiro_nome=None,
    codigo_voucher=None,
    termos=(),
):
    return PerfilComercialScout(
        fonte="awin",
        id_externo=id_externo,
        tipo_sinal="promotion",
        titulo=f"Sinal {id_externo}",
        marketplace=marketplace,
        parceiro_id=parceiro_id,
        parceiro_nome=parceiro_nome,
        codigo_voucher=codigo_voucher,
        termos_descoberta=termos,
    )


def observar(
    perfil,
    horas_atras,
):
    return ObservacaoComercialScout(
        perfil=perfil,
        observado_em=(AGORA - timedelta(hours=horas_atras)),
    )


def buscar(
    tendencias,
    dimensao,
):
    return [item for item in tendencias if item.dimensao == dimensao]


def test_um_unico_sinal_nunca_vira_tendencia():
    observacoes = [
        observar(
            criar_perfil(
                "1",
                termos=("Ryzen",),
            ),
            5,
        )
    ]

    tendencias = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
    )

    assert tendencias == []


def test_dois_sinais_distintos_podem_formar_tendencia_estavel():
    observacoes = [
        observar(
            criar_perfil(
                "1",
                termos=("Ryzen",),
            ),
            60,
        ),
        observar(
            criar_perfil(
                "2",
                termos=("Ryzen",),
            ),
            10,
        ),
    ]

    tendencias = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
    )

    termos = buscar(
        tendencias,
        "termo_discovery",
    )

    assert len(termos) == 1
    assert termos[0].sinais_distintos == 2
    assert termos[0].ocorrencias_anteriores == 1
    assert termos[0].ocorrencias_recentes == 1
    assert termos[0].direcao == "estavel"


def test_tendencia_em_alta_exige_mais_sinais_na_metade_recente():
    observacoes = [
        observar(
            criar_perfil(
                "1",
                termos=("SSD NVMe",),
            ),
            60,
        ),
        observar(
            criar_perfil(
                "2",
                termos=("SSD NVMe",),
            ),
            10,
        ),
        observar(
            criar_perfil(
                "3",
                termos=("SSD NVMe",),
            ),
            4,
        ),
    ]

    tendencias = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
    )

    tendencia = buscar(
        tendencias,
        "termo_discovery",
    )[0]

    assert tendencia.sinais_distintos == 3
    assert tendencia.ocorrencias_anteriores == 1
    assert tendencia.ocorrencias_recentes == 2
    assert tendencia.direcao == "alta"


def test_tendencia_em_queda_exige_menos_sinais_na_metade_recente():
    observacoes = [
        observar(
            criar_perfil(
                "1",
                termos=("Monitor",),
            ),
            60,
        ),
        observar(
            criar_perfil(
                "2",
                termos=("Monitor",),
            ),
            50,
        ),
        observar(
            criar_perfil(
                "3",
                termos=("Monitor",),
            ),
            5,
        ),
    ]

    tendencias = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
    )

    tendencia = buscar(
        tendencias,
        "termo_discovery",
    )[0]

    assert tendencia.ocorrencias_anteriores == 2
    assert tendencia.ocorrencias_recentes == 1
    assert tendencia.direcao == "queda"


def test_repeticoes_do_mesmo_sinal_nao_criam_tendencia_falsa():
    perfil = criar_perfil(
        "1",
        termos=("GPU",),
    )

    observacoes = [
        observar(
            perfil,
            60,
        ),
        observar(
            perfil,
            5,
        ),
    ]

    tendencias = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
    )

    assert tendencias == []


def test_sinais_fora_da_janela_sao_ignorados():
    observacoes = [
        observar(
            criar_perfil(
                "1",
                termos=("Teclado",),
            ),
            100,
        ),
        observar(
            criar_perfil(
                "2",
                termos=("Teclado",),
            ),
            5,
        ),
    ]

    tendencias = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
        janela_horas=72,
    )

    assert tendencias == []


def test_termos_equivalentes_sao_agregados_sem_diferenca_de_caixa():
    observacoes = [
        observar(
            criar_perfil(
                "1",
                termos=("Ryzen 7",),
            ),
            20,
        ),
        observar(
            criar_perfil(
                "2",
                termos=("  RYZEN   7 ",),
            ),
            10,
        ),
    ]

    tendencias = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
    )

    termos = buscar(
        tendencias,
        "termo_discovery",
    )

    assert len(termos) == 1
    assert termos[0].chave == "ryzen 7"
    assert termos[0].sinais_distintos == 2


def test_parceiro_com_id_e_agregado_pelo_id_e_nao_pelo_nome():
    observacoes = [
        observar(
            criar_perfil(
                "1",
                parceiro_id="123",
                parceiro_nome="Parceiro",
            ),
            20,
        ),
        observar(
            criar_perfil(
                "2",
                parceiro_id="123",
                parceiro_nome="Parceiro Renomeado",
            ),
            10,
        ),
    ]

    tendencias = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
    )

    parceiros = buscar(
        tendencias,
        "parceiro",
    )

    assert len(parceiros) == 1
    assert parceiros[0].chave == "id:123"
    assert parceiros[0].sinais_distintos == 2


def test_marketplace_e_cupom_sao_dimensoes_independentes():
    observacoes = [
        observar(
            criar_perfil(
                "1",
                marketplace="kabum",
                codigo_voucher="GAMER10",
            ),
            20,
        ),
        observar(
            criar_perfil(
                "2",
                marketplace="KABUM",
                codigo_voucher="gamer10",
            ),
            10,
        ),
    ]

    tendencias = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
    )

    marketplaces = buscar(
        tendencias,
        "marketplace",
    )

    cupons = buscar(
        tendencias,
        "cupom",
    )

    assert len(marketplaces) == 1
    assert marketplaces[0].chave == "kabum"

    assert len(cupons) == 1
    assert cupons[0].chave == "gamer10"


def test_datetime_sem_timezone_e_rejeitado():
    observacao = ObservacaoComercialScout(
        perfil=criar_perfil(
            "1",
            termos=("Mouse",),
        ),
        observado_em=datetime(
            2026,
            9,
            10,
            17,
            0,
        ),
    )

    with pytest.raises(
        ValueError,
        match="timezone",
    ):
        (
            AgregadorTendenciasComerciaisScout().agregar(
                [
                    observacao,
                ],
                agora=AGORA,
            )
        )
