from models.tendencia_comercial_scout import (
    TendenciaComercialScout,
)
from services.scout.inteligencia_discovery_comercial_hunter import (
    InteligenciaDiscoveryComercialHunter,
)


def _tendencia(
    *,
    dimensao: str = "marketplace",
    chave: str = "kabum",
    direcao: str = "alta",
    madura: bool = True,
    sinais: int = 5,
) -> TendenciaComercialScout:
    evidencias = ()

    if madura:
        evidencias = (
            "qualidade_temporal:aprovada",
            "ambas_metades_tem_sinais",
        )

    return TendenciaComercialScout(
        dimensao=dimensao,
        chave=chave,
        rotulo=chave,
        janela_horas=72,
        sinais_distintos=sinais,
        ocorrencias_anteriores=2,
        ocorrencias_recentes=3,
        direcao=direcao,
        evidencias=evidencias,
    )


def _base():
    return {
        "MercadoLivreScraper": 10,
        "ShopeeScraper": 10,
        "KabumScraper": 10,
        "AliExpressScraper": 5,
        "SocialScoutScraper": 5,
    }


def test_sem_tendencias_preserva_todos_os_limites():
    base = _base()

    resultado = InteligenciaDiscoveryComercialHunter().calcular(
        base,
        [],
    )

    assert resultado.como_mapping() == base

    assert resultado.houve_ajuste is False

    assert resultado.sinais == ()


def test_alta_madura_kabum_aumenta_budget_em_cinquenta_porcento():
    resultado = InteligenciaDiscoveryComercialHunter().calcular(
        _base(),
        [
            _tendencia(
                chave="kabum",
            )
        ],
    )

    assert resultado.como_mapping()["KabumScraper"] == 15

    assert resultado.fontes_impulsionadas == ("KabumScraper",)


def test_aliexpress_arredonda_aumento_para_cima():
    resultado = InteligenciaDiscoveryComercialHunter().calcular(
        _base(),
        [
            _tendencia(
                chave="AliExpress",
            )
        ],
    )

    assert resultado.como_mapping()["AliExpressScraper"] == 8


def test_aumento_absoluto_possui_teto():
    service = InteligenciaDiscoveryComercialHunter(
        fator_aumento=1.0,
        aumento_maximo=10,
    )

    resultado = service.calcular(
        {
            "KabumScraper": 100,
        },
        [
            _tendencia(
                chave="kabum",
            )
        ],
    )

    assert resultado.como_mapping()["KabumScraper"] == 110


def test_tendencia_em_queda_nao_reduz_budget():
    base = _base()

    resultado = InteligenciaDiscoveryComercialHunter().calcular(
        base,
        [
            _tendencia(
                direcao="queda",
            )
        ],
    )

    assert resultado.como_mapping() == base


def test_estavel_dimensoes_nao_marketplace_e_imatura_sao_ignoradas():
    base = _base()

    tendencias = [
        _tendencia(
            direcao="estavel",
        ),
        _tendencia(
            dimensao="cupom",
            chave="GAMER10",
        ),
        _tendencia(
            dimensao="parceiro",
            chave="123",
        ),
        _tendencia(
            dimensao="termo_discovery",
            chave="Ryzen 7",
        ),
        _tendencia(
            madura=False,
        ),
    ]

    resultado = InteligenciaDiscoveryComercialHunter().calcular(
        base,
        tendencias,
    )

    assert resultado.como_mapping() == base

    assert resultado.houve_ajuste is False


def test_marketplace_desconhecido_ou_fonte_ausente_nao_cria_budget():
    base = {
        "KabumScraper": 10,
    }

    resultado = InteligenciaDiscoveryComercialHunter().calcular(
        base,
        [
            _tendencia(
                chave="loja_inexistente",
            ),
            _tendencia(
                chave="aliexpress",
            ),
        ],
    )

    assert resultado.como_mapping() == base

    assert "AliExpressScraper" not in resultado.como_mapping()


def test_multiplas_tendencias_da_mesma_fonte_nao_empilham_bonus_e_input_nao_muda():
    base = _base()

    original = dict(base)

    resultado = InteligenciaDiscoveryComercialHunter().calcular(
        base,
        [
            _tendencia(
                chave="kabum",
                sinais=4,
            ),
            _tendencia(
                chave="KABUM",
                sinais=20,
            ),
        ],
    )

    assert resultado.como_mapping()["KabumScraper"] == 15

    assert len(resultado.sinais) == 1

    assert resultado.sinais[0].sinais_distintos == 20

    assert base == original
