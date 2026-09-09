from models.oferta import Oferta
from repositories.historico_precos_efetivos_repository import (
    HistoricoPrecosEfetivosRepository,
)
from services.historico_precos_efetivos_service import (
    HistoricoPrecosEfetivosService,
)


def oferta(
    *,
    preco_oficial: float = 6323.07,
    preco_promocional: float = 5951.07,
    tipo_promocao: str = "valor_off_com_cupom",
    confirmada: bool = True,
    grupo_confere: bool = True,
) -> Oferta:
    item = Oferta(
        nome="Notebook Gamer Acer Nitro V15 RTX 4060",
        loja="Mercado Livre",
        preco=preco_oficial,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
        marketplace="mercado_livre",
    )

    item.id_produto = "MLB54358498"

    item.origem_descoberta = "social_scout"

    item.preco_condicional_observado = preco_promocional

    item.codigo_cupom_observado = "CUPOM_SOCIAL"

    item.cupom_validado_descoberta = False

    item.promocao_marketplace_confirmada = confirmada

    item.preco_grupo_confere_promocao = grupo_confere

    item.preco_promocional_marketplace = preco_promocional

    item.tipo_promocao_marketplace = tipo_promocao

    item.fonte_promocao_marketplace = "marketplace_oficial"

    return item


def service(
    tmp_path,
):
    repository = HistoricoPrecosEfetivosRepository(tmp_path / "historico_efetivo.json")

    return HistoricoPrecosEfetivosService(
        repository=repository,
        tamanho_lote_salvamento=100,
    )


def test_preco_confirmado_entra_em_serie_separada(
    tmp_path,
):
    item = oferta()

    preco_oficial_antes = item.preco

    historico = service(tmp_path)

    resultado = historico.analisar_e_registrar(item)

    assert resultado.elegivel is True
    assert resultado.primeiro_registro is True
    assert resultado.preco_efetivo == 5951.07

    assert resultado.novo_menor_preco is False

    assert item.preco == preco_oficial_antes

    registros = historico.repository.obter_registros(resultado.chave_serie)

    assert len(registros) == 1

    assert registros[0]["preco_efetivo"] == 5951.07

    assert registros[0]["preco_oficial"] == 6323.07


def test_promocao_nao_confirmada_nao_entra(
    tmp_path,
):
    historico = service(tmp_path)

    resultado = historico.analisar_e_registrar(
        oferta(
            confirmada=False,
        )
    )

    assert resultado.elegivel is False

    assert historico.repository.quantidade_series() == 0


def test_preco_social_que_nao_confere_nao_entra(
    tmp_path,
):
    historico = service(tmp_path)

    resultado = historico.analisar_e_registrar(
        oferta(
            grupo_confere=False,
        )
    )

    assert resultado.elegivel is False

    assert historico.repository.quantidade_series() == 0


def test_segundo_preco_mais_baixo_vira_novo_minimo(
    tmp_path,
    monkeypatch,
):
    historico = service(tmp_path)

    primeiro = oferta(
        preco_promocional=6000.0,
    )

    resultado_a = historico.analisar_e_registrar(primeiro)

    assert resultado_a.primeiro_registro is True

    # Simula novo dia para o repository
    # preservar os dois pontos da serie.
    original = historico.repository._extrair_data

    chamadas = {
        "n": 0,
    }

    def datas_distintas(
        valor,
    ):
        chamadas["n"] += 1

        if chamadas["n"] >= 2:
            return "2099-01-02"

        return original(valor)

    monkeypatch.setattr(
        historico.repository,
        "_extrair_data",
        datas_distintas,
    )

    segundo = oferta(
        preco_promocional=5700.0,
    )

    resultado_b = historico.analisar_e_registrar(segundo)

    assert resultado_b.preco_anterior == 6000.0

    assert resultado_b.menor_preco_anterior == 6000.0

    assert resultado_b.novo_menor_preco is True

    assert resultado_b.queda_percentual == 5.0


def test_tipos_de_promocao_usam_series_diferentes(
    tmp_path,
):
    historico = service(tmp_path)

    cupom = historico.analisar_e_registrar(
        oferta(
            tipo_promocao=("valor_off_com_cupom"),
        )
    )

    pix = historico.analisar_e_registrar(
        oferta(
            tipo_promocao=("preco_pix"),
        )
    )

    assert cupom.chave_serie != pix.chave_serie

    assert cupom.primeiro_registro is True
    assert pix.primeiro_registro is True

    assert historico.repository.quantidade_series() == 2


def test_codigo_nao_validado_nao_impede_preco_confirmado(
    tmp_path,
):
    item = oferta()

    assert item.cupom_validado_descoberta is False

    historico = service(tmp_path)

    resultado = historico.analisar_e_registrar(item)

    assert resultado.elegivel is True

    registro = historico.repository.obter_registros(resultado.chave_serie)[0]

    assert registro["codigo_cupom_validado"] is False

    assert registro["preco_efetivo"] == 5951.07


def _semear_serie(
    historico,
    precos,
    *,
    tipo_condicao="valor_off_com_cupom",
):
    chave_serie = historico._criar_chave_serie(
        chave_produto="MLB54358498",
        marketplace="mercado_livre",
        tipo_condicao=tipo_condicao,
    )

    for indice, preco in enumerate(
        precos,
        start=1,
    ):
        historico.repository.registrar_preco_efetivo(
            chave_serie=chave_serie,
            chave_produto="MLB54358498",
            marketplace="mercado_livre",
            tipo_condicao=tipo_condicao,
            preco_efetivo=preco,
            preco_oficial=6323.07,
            coletado_em=(f"2000-01-{indice:02d}T12:00:00-03:00"),
            fonte="marketplace_oficial",
            codigo_cupom_observado=None,
            codigo_cupom_validado=False,
        )

    return chave_serie


def test_primeiro_registro_nao_inventa_baseline(
    tmp_path,
):
    historico = service(tmp_path)

    resultado = historico.analisar_e_registrar(oferta())

    assert resultado.elegivel is True

    assert resultado.preco_mediano_anterior is None

    assert resultado.quantidade_registros_baseline == 0

    assert resultado.maturidade_baseline_percentual == 0.0

    assert resultado.queda_vs_mediana_percentual == 0.0

    assert resultado.queda_vs_minimo_anterior_percentual == 0.0


def test_metricas_factuais_da_serie_efetiva(
    tmp_path,
):
    historico = service(tmp_path)

    _semear_serie(
        historico,
        [
            6000.0,
            5900.0,
            6100.0,
        ],
    )

    resultado = historico.analisar_e_registrar(
        oferta(
            preco_promocional=5700.0,
        )
    )

    assert resultado.elegivel is True
    assert resultado.preco_anterior == 6100.0
    assert resultado.menor_preco_anterior == 5900.0
    assert resultado.preco_mediano_anterior == 6000.0

    assert resultado.quantidade_registros_baseline == 3

    assert resultado.maturidade_baseline_percentual == 30.0

    assert resultado.queda_percentual == 6.56

    assert resultado.queda_vs_mediana_percentual == 5.0

    assert resultado.queda_vs_minimo_anterior_percentual == 3.39

    assert resultado.novo_menor_preco is True
    assert resultado.quantidade_registros == 4


def test_preco_acima_da_mediana_nao_gera_queda_vs_mediana(
    tmp_path,
):
    historico = service(tmp_path)

    _semear_serie(
        historico,
        [
            500.0,
            600.0,
            700.0,
        ],
    )

    resultado = historico.analisar_e_registrar(
        oferta(
            preco_oficial=1000.0,
            preco_promocional=650.0,
        )
    )

    assert resultado.preco_mediano_anterior == 600.0

    assert resultado.queda_vs_mediana_percentual == 0.0

    assert resultado.queda_vs_minimo_anterior_percentual == 0.0

    assert resultado.novo_menor_preco is False


def test_maturidade_do_baseline_e_limitada_a_cem(
    tmp_path,
):
    historico = service(tmp_path)

    precos = [1000.0 + indice for indice in range(12)]

    _semear_serie(
        historico,
        precos,
    )

    resultado = historico.analisar_e_registrar(
        oferta(
            preco_oficial=1500.0,
            preco_promocional=900.0,
        )
    )

    assert resultado.quantidade_registros_baseline == 12

    assert resultado.maturidade_baseline_percentual == 100.0


def test_condicoes_diferentes_nao_compartilham_baseline(
    tmp_path,
):
    historico = service(tmp_path)

    _semear_serie(
        historico,
        [
            1000.0,
            950.0,
            900.0,
        ],
        tipo_condicao="valor_off_com_cupom",
    )

    resultado = historico.analisar_e_registrar(
        oferta(
            preco_oficial=1200.0,
            preco_promocional=850.0,
            tipo_promocao="preco_pix",
        )
    )

    assert resultado.tipo_condicao == "preco_pix"

    assert resultado.primeiro_registro is True

    assert resultado.quantidade_registros_baseline == 0

    assert resultado.preco_mediano_anterior is None

    assert resultado.maturidade_baseline_percentual == 0.0
