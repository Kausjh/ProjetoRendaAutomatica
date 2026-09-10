from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

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
    22,
    30,
    30,
    tzinfo=UTC,
)


def _observacao(
    id_externo: str,
    instante: datetime,
    *,
    marketplace: str = "kabum",
) -> ObservacaoComercialScout:
    perfil = SimpleNamespace(
        fonte="awin",
        id_externo=id_externo,
        marketplace=marketplace,
        parceiro_id=None,
        parceiro_nome=None,
        termos_descoberta=(),
        codigo_voucher=None,
    )

    return ObservacaoComercialScout(
        perfil=perfil,
        observado_em=instante,
    )


def test_gate_bloqueia_minuto_dominante_mesmo_com_baseline_antiga():
    observacoes = [
        _observacao(
            "antigo",
            AGORA - timedelta(hours=50),
        )
    ]

    observacoes.extend(
        _observacao(
            f"recente-{indice}",
            (AGORA - timedelta(minutes=5) + timedelta(milliseconds=indice * 20)),
        )
        for indice in range(9)
    )

    resultado = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
    )

    assert resultado == []


def test_gate_bloqueia_cobertura_inferior_a_uma_hora():
    observacoes = [
        _observacao(
            "anterior",
            AGORA
            - timedelta(
                hours=1,
                minutes=15,
            ),
        ),
        _observacao(
            "recente",
            AGORA
            - timedelta(
                minutes=45,
            ),
        ),
    ]

    resultado = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
        janela_horas=2,
    )

    assert resultado == []


def test_gate_bloqueia_cold_start_so_na_metade_recente():
    observacoes = [
        _observacao(
            "a",
            AGORA - timedelta(hours=8),
        ),
        _observacao(
            "b",
            AGORA - timedelta(hours=4),
        ),
        _observacao(
            "c",
            AGORA - timedelta(hours=2),
        ),
    ]

    resultado = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
        janela_horas=72,
    )

    assert resultado == []


def test_gate_libera_tendencia_com_historico_temporal_maduro():
    observacoes = [
        _observacao(
            "antigo-1",
            AGORA - timedelta(hours=60),
        ),
        _observacao(
            "antigo-2",
            AGORA - timedelta(hours=50),
        ),
        _observacao(
            "novo-1",
            AGORA - timedelta(hours=20),
        ),
        _observacao(
            "novo-2",
            AGORA - timedelta(hours=10),
        ),
        _observacao(
            "novo-3",
            AGORA - timedelta(hours=5),
        ),
    ]

    resultado = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
        janela_horas=72,
    )

    assert len(resultado) == 1

    tendencia = resultado[0]

    assert tendencia.dimensao == "marketplace"
    assert tendencia.chave == "kabum"
    assert tendencia.direcao == "alta"

    assert "qualidade_temporal:aprovada" in tendencia.evidencias

    assert "ambas_metades_tem_sinais" in tendencia.evidencias

    assert any(evidencia.startswith("cobertura_horas:") for evidencia in tendencia.evidencias)


def test_gate_e_aplicado_independentemente_por_grupo():
    observacoes = [
        _observacao(
            "kabum-antigo-1",
            AGORA - timedelta(hours=60),
        ),
        _observacao(
            "kabum-antigo-2",
            AGORA - timedelta(hours=50),
        ),
        _observacao(
            "kabum-novo-1",
            AGORA - timedelta(hours=20),
        ),
        _observacao(
            "kabum-novo-2",
            AGORA - timedelta(hours=10),
        ),
        _observacao(
            "kabum-novo-3",
            AGORA - timedelta(hours=5),
        ),
    ]

    observacoes.extend(
        _observacao(
            f"ali-{indice}",
            (AGORA - timedelta(minutes=5) + timedelta(milliseconds=indice * 20)),
            marketplace="aliexpress",
        )
        for indice in range(5)
    )

    resultado = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
        janela_horas=72,
    )

    marketplaces = {
        tendencia.chave for tendencia in resultado if tendencia.dimensao == "marketplace"
    }

    assert marketplaces == {
        "kabum",
    }


def test_gate_bloqueia_lote_semelhante_a_primeira_coleta_real():
    observacoes = [
        _observacao(
            f"real-{indice}",
            (AGORA - timedelta(minutes=5) + timedelta(milliseconds=indice * 20)),
        )
        for indice in range(343)
    ]

    resultado = AgregadorTendenciasComerciaisScout().agregar(
        observacoes,
        agora=AGORA,
        janela_horas=72,
    )

    assert resultado == []
