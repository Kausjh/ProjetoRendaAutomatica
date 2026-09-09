from models.oferta import Oferta
from services.classificador_produto import ClassificadorProduto
from services.normalizador_produto import NormalizadorProduto


def criar(nome: str, preco: float = 1000.0) -> Oferta:
    return Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=preco,
        preco_antigo=None,
        link="https://www.mercadolivre.com.br/item",
        imagem=None,
    )


def classificar(nome: str) -> Oferta:
    oferta = criar(nome)
    ClassificadorProduto().aplicar_classificacao(oferta)
    return oferta


def test_notebook_com_ryzen_e_rtx_continua_notebook():
    oferta = classificar("Notebook Gamer Acer Nitro V15 Ryzen 7 7735HS RTX 4050 16GB 512GB SSD")
    assert oferta.categoria == "Notebook"


def test_pc_completo_com_ryzen_e_rtx_continua_computador():
    oferta = classificar("PC Gamer Ryzen 5 5500 16GB SSD 1TB RTX 4060")
    assert oferta.categoria == "Computador e Mini PC"


def test_kit_upgrade_nao_vira_processador():
    oferta = classificar("Kit Upgrade Ryzen 7 5700X + B550M Aorus Elite + 32GB RAM")
    assert oferta.categoria == "Kit upgrade"


def test_gpu_avulsa_continua_gpu():
    oferta = classificar("Placa de Vídeo Asus GeForce RTX 4060 8GB")
    assert oferta.categoria == "Placa de vídeo"


def test_notebook_nao_e_deduplicado_pela_gpu_interna():
    oferta = classificar("Notebook Gamer Acer Nitro V15 Ryzen 7 7735HS RTX 4050 16GB 512GB SSD")
    resultado = NormalizadorProduto().normalizar(oferta)
    assert resultado.nome_canonico != "RTX 4050"
    assert resultado.confianca < 90


def test_gpu_avulsa_recebe_normalizacao_de_alta_confianca():
    oferta = classificar("Placa de Vídeo Asus GeForce RTX 4060 8GB")
    resultado = NormalizadorProduto().normalizar(oferta)
    assert resultado.nome_canonico == "RTX 4060"
    assert resultado.confianca >= 90


def test_acessorio_de_headset_e_bloqueado():
    oferta = classificar("Headband Almofada Headset HyperX Cloud 2")
    assert oferta.eh_nicho is False


def test_placa_mae_com_hifen_e_canonizada():
    normalizado = ClassificadorProduto._normalizar_texto("Placa-M\u00e3e MSI B550M")

    assert normalizado == "placa mae msi b550m"


def test_b550_reais_com_hifen_continuam_placa_mae():
    titulos = (
        ("Placa-M\u00e3e Msi B550m " "Pro-Vdh Am4 Hdmi Vga"),
        ("Placa-m\u00e3e Asus P/amd Am4 " "B550m-plus Tuf Gaming " "4xddr4 Matx"),
    )

    for titulo in titulos:
        item = classificar(titulo)

        assert item.eh_nicho is True

        assert item.categoria == "Placa-m\u00e3e"

        assert item.categoria != "Mem\u00f3ria RAM"


def test_a520_com_ddr4_nao_vira_memoria_ram():
    item = classificar("Placa-m\u00e3e Msi A520m-a Pro " "Am4 Matx Ddr4 Hdmi Dvi M.2")

    assert item.eh_nicho is True

    assert item.categoria == "Placa-m\u00e3e"

    assert item.categoria != "Mem\u00f3ria RAM"


def test_b650_com_ddr5_nao_vira_memoria_ram():
    item = classificar(
        "Placa-m\u00e3e Asrock B650M-HDV/M.2 " "AMD AM5 Micro ATX DDR5 PCIe " "Gen5 2 M.2 Slots"
    )

    assert item.eh_nicho is True

    assert item.categoria == "Placa-m\u00e3e"

    assert item.categoria != "Mem\u00f3ria RAM"


def test_memorias_ddr4_e_ddr5_continuam_memoria_ram():
    titulos = (
        ("Mem\u00f3ria RAM Kingston Fury Beast " "16GB DDR4 3200MHz"),
        ("Mem\u00f3ria Corsair Vengeance " "32GB DDR5 6000MHz"),
    )

    for titulo in titulos:
        item = classificar(titulo)

        assert item.eh_nicho is True

        assert item.categoria == "Mem\u00f3ria RAM"


def test_notebook_com_componentes_continua_notebook():
    item = classificar("Notebook Lenovo IdeaPad " "Ryzen 7 16GB 512GB SSD")

    assert item.eh_nicho is True

    assert item.categoria == "Notebook"


def test_fonte_cooler_master_mwe_e_fonte_de_pc():
    item = classificar("Fonte Cooler Master Mwe 750 V3 " "750w Atx 3.1 Preto")

    assert item.eh_nicho is True
    assert item.categoria == "Fonte e energia"


def test_fonte_corsair_com_wattagem_e_fonte_de_pc():
    item = classificar("Fonte Corsair RM750e 750W " "Full Modular PCIe 5.0")

    assert item.eh_nicho is True
    assert item.categoria == "Fonte e energia"


def test_fonte_msi_80_plus_continua_fonte_de_pc():
    item = classificar("Fonte Msi Mag A650bn 650w " "80 Plus Bronze Pfc Ativo Preto")

    assert item.eh_nicho is True
    assert item.categoria == "Fonte e energia"


def test_fonte_baixa_potencia_nao_e_forcada_como_psu():
    item = classificar("Fonte Carregador Notebook Dell " "65W USB-C")

    assert item.categoria != "Fonte e energia"
