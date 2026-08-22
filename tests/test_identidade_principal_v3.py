from models.oferta import Oferta
from services.classificador_produto import ClassificadorProduto
from services.normalizador_produto import NormalizadorProduto


def oferta(nome: str) -> Oferta:
    return Oferta(
        nome=nome,
        loja="Mercado Livre",
        preco=500.0,
        preco_antigo=None,
        link="https://mercadolivre.com.br/teste",
        imagem=None,
    )


def classificar(nome: str) -> Oferta:
    item = oferta(nome)
    ClassificadorProduto().aplicar_classificacao(item)
    return item


def test_ssd_para_notebook_continua_armazenamento():
    item = classificar("Ssd M.2 500gb Wd Green Sn350 2280 Nvme Pcie Gen 3.0 Para Pc E Notebook")
    assert item.categoria == "Armazenamento"


def test_ssd_para_ps5_nao_vira_console():
    item = classificar("SSD M.2 2TB UP Gamer Titan Edition PCIe Gen5 Para PC e PS5")
    assert item.categoria == "Armazenamento"
    r = NormalizadorProduto().normalizar(item)
    assert r.nome_canonico != "PlayStation 5"
    assert r.confianca < 90


def test_headset_ps4_ps5_nao_vira_console():
    item = classificar("Headset Gamer Cloud Stinger Core Xbox PS4 PS5 HyperX")
    assert item.categoria == "Áudio"
    r = NormalizadorProduto().normalizar(item)
    assert not r.chave_canonica.startswith("playstation_")


def test_controle_para_ps5_e_controle():
    assert classificar("Controle sem fio Gamepad para PS5 PC Bluetooth").categoria == "Controle"


def test_suporte_para_ps5_e_suporte():
    assert (
        classificar("Suporte Base Vertical para PS5 com Carregador").categoria
        == "Suportes e conectividade"
    )


def test_computador_bluepc_com_geforce_e_computador():
    assert (
        classificar(
            "Computador Bluepc Pro Intel Core i5 12400f 8GB DDR4 SSD 256gb "
            "Gráficos Geforce Fonte 500w Windows 11"
        ).categoria
        == "Computador e Mini PC"
    )


def test_computador_slim_com_ssd_e_computador():
    assert (
        classificar("Computador Slim Intel I7 16gb Ssd 512gb Mon 19 Strong Tech").categoria
        == "Computador e Mini PC"
    )


def test_pc_bestpc_e_computador():
    assert (
        classificar("PC BestPc Intel Core i5 8GB 256GB HDD Windows 10 Corporativo").categoria
        == "Computador e Mini PC"
    )


def test_kit_ryzen_b550_sem_palavra_upgrade_e_kit():
    assert (
        classificar("Kit Ryzen 7 5700x / Placa Mãe Gigabyte B550m Aorus Elite").categoria
        == "Kit upgrade"
    )


def test_kit_ryzen_b650_ram_e_kit():
    assert (
        classificar("Kit Amd Ryzen 7 7700x + Gigabyte B650m Aorus Elite + 32 Gb").categoria
        == "Kit upgrade"
    )


def test_processador_para_notebook_continua_processador():
    assert (
        classificar("Processador P/ Notebook Intel Core I5 3340m SR0XA 3a Geração").categoria
        == "Processador"
    )


def test_playstation_real_recebe_canonical_alta_confianca():
    item = classificar("Sony PlayStation 5 Slim Digital 1TB Branco")
    assert item.categoria == "Console"
    r = NormalizadorProduto().normalizar(item)
    assert r.nome_canonico == "PlayStation 5"
    assert r.confianca >= 90


def test_console_forcado_com_acessorio_nao_recebe_canonical_ps5():
    item = oferta("SSD NVMe 1TB com dissipador compatível com PS5")
    item.categoria = "Console"
    r = NormalizadorProduto().normalizar(item)
    assert r.nome_canonico != "PlayStation 5"
    assert r.confianca < 90
