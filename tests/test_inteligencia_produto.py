from models.oferta import Oferta
from services.classificador_produto import ClassificadorProduto
from services.inteligencia_produto import (
    InteligenciaProduto,
)


def oferta(
    nome: str,
    categoria: str,
    preco: float = 1000.0,
) -> Oferta:
    item = Oferta(
        nome=nome,
        loja="Teste",
        preco=preco,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
    )

    item.categoria = categoria
    item.eh_nicho = True
    item.relevancia_nicho = 90.0

    return item


def test_rtx_5070_e_muito_desejavel():
    resultado = InteligenciaProduto().analisar(
        oferta(
            "Placa de Video NVIDIA GeForce RTX 5070 12GB GDDR7",
            "Placa de video",
        )
    )

    assert resultado.nota >= 90
    assert resultado.nivel == "muito_alto"
    assert resultado.modelo == "RTX 5070"


def test_rtx_5060_e_muito_desejavel():
    resultado = InteligenciaProduto().analisar(
        oferta(
            "INNO3D NVIDIA GeForce RTX5060 8GB Twin X2 OC",
            "Placa de video",
        )
    )

    assert resultado.nota >= 90
    assert resultado.modelo == "RTX 5060"


def test_ryzen_5700x_e_muito_desejavel():
    resultado = InteligenciaProduto().analisar(
        oferta(
            "Processador AMD Ryzen 7 5700X",
            "Processador",
        )
    )

    assert resultado.nota >= 85

    assert resultado.modelo == "Ryzen 7 5700X"


def test_ultragear_tem_prioridade_alta():
    resultado = InteligenciaProduto().analisar(
        oferta(
            "Monitor Gamer LG UltraGear 24 180Hz IPS",
            "Monitor",
        )
    )

    assert resultado.nota >= 75

    assert resultado.nivel in {
        "alto",
        "muito_alto",
    }


def test_b550_tuf_tem_prioridade_alta():
    resultado = InteligenciaProduto().analisar(
        oferta(
            "Placa Mae B550M TUF Gaming",
            "Placa-mae",
        )
    )

    assert resultado.nota >= 70

    assert resultado.nivel in {
        "alto",
        "muito_alto",
    }


def test_produto_generico_fica_baixo():
    resultado = InteligenciaProduto().analisar(
        oferta(
            "Mouse Gamer RGB Generico Modelo XPTO",
            "Mouse",
        )
    )

    assert resultado.nota < 40
    assert resultado.nivel == "baixo"


def test_preco_nao_altera_nota_produto():
    inteligencia = InteligenciaProduto()

    barato = inteligencia.analisar(
        oferta(
            "NVIDIA GeForce RTX 5070 12GB",
            "Placa de video",
            preco=1000,
        )
    )

    caro = inteligencia.analisar(
        oferta(
            "NVIDIA GeForce RTX 5070 12GB",
            "Placa de video",
            preco=10000,
        )
    )

    assert barato.nota == caro.nota

    assert barato.confianca == caro.confianca


def test_aplicar_persiste_metadados_na_oferta():
    item = oferta(
        "Monitor Gamer LG UltraGear 27 180Hz",
        "Monitor",
    )

    resultado = InteligenciaProduto().aplicar(item)

    assert item.nota_produto == resultado.nota

    assert item.confianca_produto == resultado.confianca

    assert item.nivel_desejabilidade == resultado.nivel

    assert item.motivos_produto

    assert item.modelo_produto == "LG UltraGear"


def test_rx_9060_xt_aceita_variacoes_de_espacamento():
    inteligencia = InteligenciaProduto()

    titulos = (
        "AMD Radeon RX 9060 XT 16GB",
        "AMD Radeon RX 9060XT 16GB",
        "AMD Radeon RX9060 XT 16GB",
        "AMD Radeon RX9060XT 16GB",
    )

    for titulo in titulos:
        item = oferta(
            titulo,
            "Placa de video",
        )

        resultado = inteligencia.analisar(item)

        assert resultado.modelo == "RX 9060 XT"

        assert resultado.familia == "RX 9060 XT"

        assert resultado.pontos_modelo == 35.0


def test_rx_9060_xt_titulo_real_mercado_livre():
    item = oferta(
        ("Gpu Powercolor Amd Radeon " "Rx 9060xt 16gb Gddr6 " "128bits 16g-a"),
        "Placa de video",
    )

    resultado = InteligenciaProduto().analisar(item)

    assert resultado.modelo == "RX 9060 XT"

    assert resultado.familia == "RX 9060 XT"

    assert resultado.pontos_modelo == 35.0

    assert resultado.marca == "AMD"

    assert resultado.nota >= 80.0


def test_rx_9060_sem_xt_nao_vira_rx_9060_xt():
    item = oferta(
        "AMD Radeon RX 9060 16GB",
        "Placa de video",
    )

    resultado = InteligenciaProduto().analisar(item)

    assert resultado.modelo != "RX 9060 XT"


def test_rx_9060_xtx_nao_vira_rx_9060_xt():
    item = oferta(
        "AMD Radeon RX 9060 XTX 16GB",
        "Placa de video",
    )

    resultado = InteligenciaProduto().analisar(item)

    assert resultado.modelo != "RX 9060 XT"


def test_rx_9060_xt_integracao_com_classificador_real():
    item = Oferta(
        nome=("Gpu Powercolor Amd Radeon " "Rx 9060xt 16gb Gddr6 " "128bits 16g-a"),
        loja="Mercado Livre",
        preco=3670.0,
        preco_antigo=4003.98,
        link="https://example.com/rx9060xt",
        imagem=None,
        marketplace="mercado_livre",
    )

    classificacao = ClassificadorProduto().aplicar_classificacao(item)

    assert classificacao.eh_nicho is True

    assert item.categoria in {
        "Placa de video",
        "Placa de vídeo",
    }

    resultado = InteligenciaProduto().analisar(item)

    assert resultado.modelo == "RX 9060 XT"

    assert resultado.familia == "RX 9060 XT"

    assert resultado.marca == "AMD"

    assert resultado.nota >= 80.0
