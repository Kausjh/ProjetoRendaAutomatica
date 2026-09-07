from unittest.mock import Mock

from models.resultado_deteccao_social_scout import (
    ResultadoDeteccaoSocialScout,
)
from models.resultado_resolucao_social_scout import (
    ResultadoResolucaoSocialScout,
)
from services.scout.validador_preco_ml_social_scout import (
    ValidadorPrecoMercadoLivreSocialScout,
)

URL = "https://www.mercadolivre.com.br/" "produto-teste/p/MLB12345678"


def deteccao(
    *,
    preco_original: float | None = 500.00,
    preco_oferta: float | None = 300.00,
    preco_final: float | None = 270.00,
    cupom: str | None = "TESTE10",
    desconto_cupom: float | None = 10.0,
):
    return ResultadoDeteccaoSocialScout(
        classificacao="oferta_produto",
        utilizavel=True,
        titulo="Produto Teste",
        marketplace="mercado_livre",
        preco_original=preco_original,
        preco_oferta=preco_oferta,
        preco_final=preco_final,
        desconto_cupom_percentual=desconto_cupom,
        codigo_cupom=cupom,
        links=("https://meli.la/teste",),
        motivo="teste",
    )


def resolucao(
    *,
    status: str = "resolvido",
    marketplace: str = "mercado_livre",
):
    return ResultadoResolucaoSocialScout(
        fonte="telegram",
        id_externo="-100123:10",
        status=status,
        marketplace=marketplace,
        tipo_destino="produto",
        url_original="https://meli.la/teste",
        url_destino=URL,
        id_produto="MLB12345678",
        motivo="teste",
    )


def snapshot(
    *,
    preco_oficial: float | None = 300.00,
    preco_original: float | None = 500.00,
    disponivel: bool | None = True,
):
    return {
        "titulo": "Produto Teste Oficial",
        "preco_oficial": preco_oficial,
        "preco_original": preco_original,
        "tipo_preco": "pix",
        "preco_parcelado": 320.00,
        "parcelas": 8,
        "valor_parcela": 40.00,
        "disponivel": disponivel,
        "preco_valido_ate": "2026-09-09",
    }


def criar_validador(
    retorno_snapshot,
):
    validador = ValidadorPrecoMercadoLivreSocialScout()

    validador._capturar_snapshot = Mock(return_value=retorno_snapshot)

    return validador


def test_valida_preco_base_e_preco_original():
    validador = criar_validador(snapshot())

    resultado = validador.validar(
        deteccao(),
        resolucao(),
    )

    assert resultado.status == "validado"
    assert resultado.preco_oficial == 300.00
    assert resultado.preco_original_oficial == 500.00

    assert resultado.preco_base_confere is True
    assert resultado.preco_original_confere is True

    assert resultado.tipo_preco_oficial == "pix"

    assert resultado.preco_parcelado_oficial == 320.00
    assert resultado.parcelas == 8
    assert resultado.valor_parcela == 40.00


def test_cupom_coerente_nao_e_marcado_como_validado():
    validador = criar_validador(snapshot())

    resultado = validador.validar(
        deteccao(),
        resolucao(),
    )

    assert resultado.preco_final_coerente_com_desconto is True

    assert resultado.cupom_validado is False

    assert resultado.motivo == ("preco_base_oficial_confere_" "cupom_ainda_nao_validado")


def test_preco_base_divergente_e_rejeitado():
    validador = criar_validador(snapshot(preco_oficial=320.00))

    resultado = validador.validar(
        deteccao(),
        resolucao(),
    )

    assert resultado.status == "divergente"
    assert resultado.preco_base_confere is False


def test_preco_original_divergente_e_rejeitado():
    validador = criar_validador(snapshot(preco_original=600.00))

    resultado = validador.validar(
        deteccao(),
        resolucao(),
    )

    assert resultado.status == "divergente"
    assert resultado.preco_original_confere is False


def test_calculo_de_cupom_divergente_e_rejeitado():
    validador = criar_validador(snapshot())

    resultado = validador.validar(
        deteccao(
            preco_final=250.00,
        ),
        resolucao(),
    )

    assert resultado.status == "divergente"

    assert resultado.preco_final_coerente_com_desconto is False

    assert resultado.cupom_validado is False


def test_produto_fora_de_estoque_e_rejeitado():
    validador = criar_validador(snapshot(disponivel=False))

    resultado = validador.validar(
        deteccao(),
        resolucao(),
    )

    assert resultado.status == "indisponivel"
    assert resultado.disponivel is False


def test_resolucao_de_outro_marketplace_nao_abre_browser():
    validador = ValidadorPrecoMercadoLivreSocialScout()

    validador._capturar_snapshot = Mock()

    resultado = validador.validar(
        deteccao(),
        resolucao(marketplace="kabum"),
    )

    validador._capturar_snapshot.assert_not_called()

    assert resultado.status == "nao_suportado"


def test_erro_quando_preco_oficial_nao_e_encontrado():
    validador = criar_validador(snapshot(preco_oficial=None))

    resultado = validador.validar(
        deteccao(),
        resolucao(),
    )

    assert resultado.status == "erro"

    assert resultado.motivo == "preco_oficial_nao_encontrado"


def test_preco_condicional_sem_base_vira_nao_verificavel():
    validador = criar_validador(snapshot())

    resultado = validador.validar(
        deteccao(
            preco_original=None,
            preco_oferta=None,
            preco_final=278.89,
            cupom="TESTE10",
            desconto_cupom=None,
        ),
        resolucao(),
    )

    assert resultado.status == "nao_verificavel"

    assert resultado.motivo == "mensagem_social_sem_preco_base"
