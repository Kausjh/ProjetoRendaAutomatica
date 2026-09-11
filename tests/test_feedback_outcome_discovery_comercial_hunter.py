# 63.8738, -149.7525

from models.oferta import Oferta
from models.resultado_hunter_v2 import (
    CandidatoHunterV2,
    ResultadoFonteHunterV2,
    ResultadoHunterV2,
)
from services.scout.feedback_outcome_discovery_comercial_hunter import (
    criar_feedback_outcome_discovery_comercial_hunter,
)


def criar_oferta(
    nome: str,
    link: str,
) -> Oferta:
    return Oferta(
        nome=nome,
        loja="Teste",
        preco=100.0,
        preco_antigo=None,
        link=link,
        imagem=None,
    )


def criar_observabilidade(
    *fontes: str,
) -> dict:
    return {
        "schema_version": 1,
        "status": "aplicado",
        "alvos": [
            {
                "fonte_hunter": fonte,
                "aplicado": True,
            }
            for fonte in fontes
        ],
    }


def criar_resultado(
    *,
    candidatos,
    fontes,
) -> ResultadoHunterV2:
    return ResultadoHunterV2(
        candidatos=tuple(candidatos),
        fontes=tuple(fontes),
        duplicatas=(),
        quantidade_bruta=sum(fonte.quantidade_coletada for fonte in fontes),
        quantidade_unica=len(candidatos),
        duplicadas_confirmadas=0,
    )


def test_sem_alvos_aplicados_retorna_estado_neutro():
    resultado = criar_feedback_outcome_discovery_comercial_hunter(
        observabilidade={
            "alvos": [],
        },
        resultado_hunter=None,
    )

    assert resultado["status"] == "sem_alvos_aplicados"

    assert resultado["fontes"] == []

    assert resultado["atribuicao_alvo_individual"] is False


def test_resultado_hunter_ausente_e_explicito():
    resultado = criar_feedback_outcome_discovery_comercial_hunter(
        observabilidade=(
            criar_observabilidade(
                "KabumScraper",
            )
        ),
        resultado_hunter=None,
    )

    assert resultado["status"] == "sem_resultado_hunter"

    assert resultado["fontes_total"] == 1

    assert resultado["fontes"][0]["status"] == "fonte_ausente_resultado_hunter"


def test_mede_funil_da_fonte_guiada():
    primeira = criar_oferta(
        "Produto A",
        "https://example.com/a",
    )

    segunda = criar_oferta(
        "Produto B",
        "https://example.com/b",
    )

    terceira = criar_oferta(
        "Produto C",
        "https://example.com/c",
    )

    resultado_hunter = criar_resultado(
        candidatos=[
            CandidatoHunterV2(
                oferta=primeira,
                fontes=("KabumScraper",),
            ),
            CandidatoHunterV2(
                oferta=segunda,
                fontes=("KabumScraper",),
            ),
            CandidatoHunterV2(
                oferta=terceira,
                fontes=("KabumScraper",),
            ),
        ],
        fontes=[
            ResultadoFonteHunterV2(
                fonte=("KabumScraper"),
                limite_solicitado=10,
                quantidade_coletada=4,
                quantidade_novas=3,
                quantidade_duplicadas=1,
            ),
        ],
    )

    resultado = criar_feedback_outcome_discovery_comercial_hunter(
        observabilidade=(
            criar_observabilidade(
                "KabumScraper",
            )
        ),
        resultado_hunter=(resultado_hunter),
        ofertas_elegiveis=[
            primeira,
            segunda,
        ],
        ofertas_selecionadas_fila=[
            segunda,
        ],
    )

    fonte = resultado["fontes"][0]

    assert resultado["status"] == "observado"

    assert fonte["limite_solicitado"] == 10

    assert fonte["quantidade_coletada"] == 4

    assert fonte["quantidade_novas"] == 3

    assert fonte["quantidade_duplicadas"] == 1

    assert fonte["elegiveis_atribuidas"] == 2

    assert fonte["selecionadas_fila_atribuidas"] == 1

    assert fonte["taxa_elegibilidade_percentual"] == 66.67

    assert fonte["taxa_selecao_fila_percentual"] == 33.33


def test_oferta_multifonte_credita_as_duas_fontes():
    oferta = criar_oferta(
        "SSD",
        "https://example.com/ssd",
    )

    resultado_hunter = criar_resultado(
        candidatos=[
            CandidatoHunterV2(
                oferta=oferta,
                fontes=(
                    "KabumScraper",
                    "AliExpressScraper",
                ),
            ),
        ],
        fontes=[
            ResultadoFonteHunterV2(
                fonte=("KabumScraper"),
                limite_solicitado=10,
                quantidade_coletada=1,
                quantidade_novas=1,
            ),
            ResultadoFonteHunterV2(
                fonte=("AliExpressScraper"),
                limite_solicitado=5,
                quantidade_coletada=1,
                quantidade_novas=1,
            ),
        ],
    )

    resultado = criar_feedback_outcome_discovery_comercial_hunter(
        observabilidade=(
            criar_observabilidade(
                "KabumScraper",
                "AliExpressScraper",
            )
        ),
        resultado_hunter=(resultado_hunter),
        ofertas_elegiveis=[
            oferta,
        ],
        ofertas_selecionadas_fila=[
            oferta,
        ],
    )

    por_fonte = {item["fonte_hunter"]: item for item in resultado["fontes"]}

    assert por_fonte["KabumScraper"]["elegiveis_atribuidas"] == 1

    assert por_fonte["AliExpressScraper"]["elegiveis_atribuidas"] == 1


def test_alvo_nao_aplicado_nao_entra_no_feedback():
    resultado = criar_feedback_outcome_discovery_comercial_hunter(
        observabilidade={
            "alvos": [
                {
                    "fonte_hunter": ("KabumScraper"),
                    "aplicado": False,
                },
            ],
        },
        resultado_hunter=None,
    )

    assert resultado["status"] == "sem_alvos_aplicados"


def test_multiplos_alvos_da_mesma_fonte_sao_contados():
    observabilidade = {
        "alvos": [
            {
                "fonte_hunter": ("KabumScraper"),
                "aplicado": True,
            },
            {
                "fonte_hunter": ("KabumScraper"),
                "aplicado": True,
            },
        ],
    }

    oferta = criar_oferta(
        "CPU",
        "https://example.com/cpu",
    )

    resultado_hunter = criar_resultado(
        candidatos=[
            CandidatoHunterV2(
                oferta=oferta,
                fontes=("KabumScraper",),
            ),
        ],
        fontes=[
            ResultadoFonteHunterV2(
                fonte=("KabumScraper"),
                limite_solicitado=10,
                quantidade_coletada=1,
                quantidade_novas=1,
            ),
        ],
    )

    resultado = criar_feedback_outcome_discovery_comercial_hunter(
        observabilidade=(observabilidade),
        resultado_hunter=(resultado_hunter),
    )

    assert resultado["fontes"][0]["alvos_aplicados"] == 2


def test_fonte_guiada_ausente_gera_feedback_parcial():
    oferta = criar_oferta(
        "CPU",
        "https://example.com/cpu",
    )

    resultado_hunter = criar_resultado(
        candidatos=[
            CandidatoHunterV2(
                oferta=oferta,
                fontes=("KabumScraper",),
            ),
        ],
        fontes=[
            ResultadoFonteHunterV2(
                fonte=("KabumScraper"),
                limite_solicitado=10,
                quantidade_coletada=1,
                quantidade_novas=1,
            ),
        ],
    )

    resultado = criar_feedback_outcome_discovery_comercial_hunter(
        observabilidade=(
            criar_observabilidade(
                "KabumScraper",
                "FonteInexistente",
            )
        ),
        resultado_hunter=(resultado_hunter),
    )

    assert resultado["status"] == "observado_parcialmente"

    por_fonte = {item["fonte_hunter"]: item for item in resultado["fontes"]}

    assert por_fonte["FonteInexistente"]["status"] == "fonte_ausente_resultado_hunter"


def test_nao_finge_atribuicao_por_termo():
    oferta = criar_oferta(
        "Ryzen",
        "https://example.com/ryzen",
    )

    resultado_hunter = criar_resultado(
        candidatos=[
            CandidatoHunterV2(
                oferta=oferta,
                fontes=("KabumScraper",),
            ),
        ],
        fontes=[
            ResultadoFonteHunterV2(
                fonte=("KabumScraper"),
                limite_solicitado=10,
                quantidade_coletada=1,
                quantidade_novas=1,
            ),
        ],
    )

    resultado = criar_feedback_outcome_discovery_comercial_hunter(
        observabilidade=(
            criar_observabilidade(
                "KabumScraper",
            )
        ),
        resultado_hunter=(resultado_hunter),
    )

    assert resultado["granularidade"] == "fonte_hunter"

    assert resultado["atribuicao_alvo_individual"] is False

    assert "termo" not in resultado["fontes"][0]
