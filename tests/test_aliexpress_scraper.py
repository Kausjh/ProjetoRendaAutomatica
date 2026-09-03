from dataclasses import replace

from models.oferta import Oferta
from scrapers.aliexpress_scraper import (
    AliExpressScraper,
)
from services.awin_product_feed_service import (
    ProdutoFeedAwin,
)
from services.classificador_produto import (
    ClassificadorProduto,
)
from services.validador_preco_aliexpress import (
    ResultadoPrecoAliExpress,
)


def produto(
    produto_id: str,
    nome: str,
    *,
    preco_feed: float = 8.96,
    moeda: str = "CNY",
    desconto: float | None = 20.0,
) -> ProdutoFeedAwin:
    return ProdutoFeedAwin(
        feed_id="47217",
        aw_product_id=(f"awin-{produto_id}"),
        merchant_product_id=produto_id,
        nome=nome,
        moeda=moeda,
        preco_feed=preco_feed,
        preco_base_feed=None,
        desconto_percentual_feed=desconto,
        estoque=None,
        categoria_merchant="",
        categoria_awin="",
        marca="",
        link_merchant="",
        link_awin="",
        aw_image_url="",
        alternate_image=("https://ae-pic-a1." "aliexpress-media.com/" "produto.jpg"),
        alternate_image_two="",
        alternate_image_three="",
        alternate_image_four="",
    )


class FeedServiceFake:
    def __init__(
        self,
        por_feed,
    ):
        self.por_feed = por_feed
        self.chamadas = []

    def iterar_produtos(
        self,
        feed_id,
        limite=None,
        advertiser_id="18879",
    ):
        self.chamadas.append(
            (
                feed_id,
                limite,
            )
        )

        itens = self.por_feed.get(
            feed_id,
            [],
        )

        if limite is None:
            yield from itens
            return

        yield from itens[:limite]


class PrecoServiceFake:
    def __init__(
        self,
        resultados,
    ):
        self.resultados = resultados
        self.ids_recebidos = []

    def validar_produtos(
        self,
        produto_ids,
    ):
        self.ids_recebidos = list(produto_ids)

        return {
            produto_id: self.resultados[produto_id]
            for produto_id in self.ids_recebidos
            if produto_id in self.resultados
        }


def preco_valido(
    produto_id,
    *,
    principal,
    normal=None,
    promocional=None,
    novo_usuario=None,
    promocao_novo_usuario=False,
    sku_atributo=None,
):
    return ResultadoPrecoAliExpress(
        produto_id=produto_id,
        preco_brl=principal,
        moeda="BRL",
        url_produto=("https://pt.aliexpress.com/" f"item/{produto_id}.html"),
        valido=True,
        motivo="ok",
        preco_normal_brl=normal,
        moeda_normal=("BRL" if normal is not None else None),
        preco_promocional_brl=promocional,
        moeda_promocional=("BRL" if promocional is not None else None),
        preco_novo_usuario_brl=novo_usuario,
        moeda_novo_usuario=("BRL" if novo_usuario is not None else None),
        promocao_novo_usuario=(promocao_novo_usuario),
        sku_id="sku-1",
        sku_atributo_selecionado=(sku_atributo),
    )


def criar_scraper(
    produtos,
    resultados,
):
    feed = FeedServiceFake(
        {
            "47217": produtos,
        }
    )

    preco = PrecoServiceFake(resultados)

    scraper = AliExpressScraper(
        feed_service=feed,
        preco_service=preco,
        feed_ids=("47217",),
        itens_por_feed=30,
        candidatos_por_feed=10,
        max_validacoes=10,
        deslocamento_feed=0,
    )

    return scraper, feed, preco


def test_filtra_fora_do_nicho_antes_do_browser():
    tech = produto(
        "1001",
        "Mini PC Ryzen 7 DDR5 NVMe",
    )

    roupa = produto(
        "1002",
        "Women's Summer Floral Dress",
    )

    scraper, _, preco = criar_scraper(
        [
            roupa,
            tech,
        ],
        {
            "1001": preco_valido(
                "1001",
                principal=999.90,
            )
        },
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert preco.ids_recebidos == ["1001"]

    assert len(ofertas) == 1


def test_promocao_comum_vira_preco_e_preco_antigo():
    item = produto(
        "2001",
        "SSD NVMe 1TB PCIe 4.0",
        preco_feed=2.38,
        moeda="USD",
    )

    scraper, _, _ = criar_scraper(
        [item],
        {
            "2001": preco_valido(
                "2001",
                principal=9.51,
                normal=10.01,
                promocional=9.51,
            )
        },
    )

    oferta = scraper.buscar_ofertas(limite=1)[0]

    assert oferta.preco == 9.51
    assert oferta.preco_antigo == 10.01

    assert oferta.desconto_percentual == 5.0

    assert oferta.preco_origem == 2.38
    assert oferta.moeda_origem == "USD"

    assert oferta.preco_novo_usuario is None


def test_promocao_novo_usuario_fica_separada():
    item = produto(
        "3001",
        "Lenovo Wireless Earbuds Bluetooth",
        preco_feed=8.96,
        moeda="CNY",
    )

    scraper, _, _ = criar_scraper(
        [item],
        {
            "3001": preco_valido(
                "3001",
                principal=40.04,
                normal=40.04,
                promocional=25.04,
                novo_usuario=25.04,
                promocao_novo_usuario=True,
            )
        },
    )

    oferta = scraper.buscar_ofertas(limite=1)[0]

    assert oferta.preco == 40.04

    assert oferta.preco_antigo is None

    assert oferta.preco_novo_usuario == 25.04

    assert oferta.moeda_novo_usuario == "R$"

    assert oferta.preco_origem == 8.96
    assert oferta.moeda_origem == "CNY"


def test_resultado_de_preco_invalido_e_descartado():
    ruim = produto(
        "4001",
        "SSD NVMe 1TB",
    )

    bom = produto(
        "4002",
        "SSD NVMe 2TB",
    )

    invalido = ResultadoPrecoAliExpress(
        produto_id="4001",
        preco_brl=None,
        moeda=None,
        url_produto=None,
        valido=False,
        motivo="preco indisponivel",
    )

    scraper, _, _ = criar_scraper(
        [
            ruim,
            bom,
        ],
        {
            "4001": invalido,
            "4002": preco_valido(
                "4002",
                principal=399.90,
            ),
        },
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert len(ofertas) == 1
    assert ofertas[0].id_produto == "4002"


def test_oferta_usa_identidade_canonica_aliexpress():
    item = produto(
        "5001",
        "Mini PC Ryzen 7 16GB DDR5",
    )

    scraper, _, _ = criar_scraper(
        [item],
        {
            "5001": preco_valido(
                "5001",
                principal=1074.99,
                normal=2443.16,
                promocional=1074.99,
            )
        },
    )

    oferta = scraper.buscar_ofertas(limite=1)[0]

    assert oferta.loja == "AliExpress"

    assert oferta.marketplace == "aliexpress"

    assert oferta.id_produto == "5001"

    assert oferta.link == ("https://pt.aliexpress.com/" "item/5001.html")

    assert oferta.moeda == "R$"


def test_respeita_limite_de_saida():
    itens = [
        produto(
            str(6000 + indice),
            f"SSD NVMe {indice + 1}TB",
        )
        for indice in range(4)
    ]

    resultados = {
        item.merchant_product_id: preco_valido(
            item.merchant_product_id,
            principal=100.0 + indice,
        )
        for indice, item in enumerate(itens)
    }

    scraper, _, _ = criar_scraper(
        itens,
        resultados,
    )

    ofertas = scraper.buscar_ofertas(limite=2)

    assert len(ofertas) == 2


def test_remove_produto_duplicado_entre_feeds():
    item = produto(
        "7001",
        "SSD NVMe 1TB",
    )

    feed = FeedServiceFake(
        {
            "47215": [item],
            "47217": [item],
        }
    )

    preco = PrecoServiceFake(
        {
            "7001": preco_valido(
                "7001",
                principal=299.90,
            )
        }
    )

    scraper = AliExpressScraper(
        feed_service=feed,
        preco_service=preco,
        feed_ids=(
            "47215",
            "47217",
        ),
        itens_por_feed=30,
        candidatos_por_feed=10,
        max_validacoes=10,
        deslocamento_feed=0,
    )

    ofertas = scraper.buscar_ofertas(limite=5)

    assert preco.ids_recebidos == ["7001"]

    assert len(ofertas) == 1


def test_deslocamento_rotativo_pula_inicio_do_feed():
    ignorado = produto(
        "8001",
        "SSD NVMe 500GB",
    )

    escolhido = produto(
        "8002",
        "Mini PC Ryzen 7 DDR5",
    )

    feed = FeedServiceFake(
        {
            "47217": [
                ignorado,
                escolhido,
            ],
        }
    )

    preco = PrecoServiceFake(
        {
            "8002": preco_valido(
                "8002",
                principal=999.90,
            )
        }
    )

    scraper = AliExpressScraper(
        feed_service=feed,
        preco_service=preco,
        feed_ids=("47217",),
        itens_por_feed=1,
        candidatos_por_feed=5,
        max_validacoes=5,
        deslocamento_feed=1,
    )

    ofertas = scraper.buscar_ofertas(limite=1)

    assert preco.ids_recebidos == ["8002"]

    assert len(ofertas) == 1


def _oferta_para_classificar(
    nome: str,
) -> Oferta:
    return Oferta(
        nome=nome,
        loja="Teste",
        preco=100.0,
        preco_antigo=None,
        link="https://example.com/item",
        imagem=None,
    )


def test_pc_com_hardware_real_e_computador_principal():
    oferta = _oferta_para_classificar(
        "Intel i9 8950HK Compact Portable PC "
        "16GB DDR4 M.2 NVMe SSD Triple 4K "
        "Display Port WiFi6"
    )

    resultado = ClassificadorProduto().classificar(oferta)

    assert resultado.categoria == "Computador e Mini PC"


def test_pc_em_caixa_eletrica_nao_vira_computador():
    oferta = _oferta_para_classificar(
        "DONGY 12WAY PC Plastic Outdoor " "Electrical IP65 Waterproof " "Distribution Box"
    )

    resultado = ClassificadorProduto().classificar(oferta)

    assert resultado.categoria != "Computador e Mini PC"


def test_chave_de_precisao_ingles_vira_maker():
    oferta = _oferta_para_classificar(
        "Precision Screwdriver Set " "25 in 1 Magnetic Repair Tool " "for iPhone Xiaomi Laptop"
    )

    resultado = ClassificadorProduto().classificar(oferta)

    assert resultado.eh_nicho is True

    assert resultado.categoria == "Maker e bancada"


def test_pre_filtro_remove_acessorio_de_celular():
    item = replace(
        produto(
            "9001",
            "66Pcs Type C Port Mobile Phone "
            "Charging Dust Plug With "
            "Earphones Cleaner Kit Brush "
            "For iPhone",
        ),
        feed_id="47245",
    )

    feed = FeedServiceFake(
        {
            "47245": [
                item,
            ],
        }
    )

    scraper = AliExpressScraper(
        feed_service=feed,
        preco_service=PrecoServiceFake({}),
        feed_ids=("47245",),
        itens_por_feed=10,
        candidatos_por_feed=10,
        max_validacoes=5,
        deslocamento_feed=0,
    )

    assert scraper._buscar_candidatos() == []


def test_remove_mini_pcs_quase_iguais():
    primeiro = replace(
        produto(
            "9101",
            "Intel Core i9 10980HK Compact "
            "Small Gaming Desktop Windows 11 "
            "16GB DDR4 RAM 2TB SSD WiFi 6 "
            "BT5.2 4K HD Gamer Mini PC",
        ),
        feed_id="47215",
    )

    segundo = replace(
        produto(
            "9102",
            "Intel Core i9 10980HK Small "
            "Desktop Gaming Computer Windows "
            "11 16GB DDR4 RAM 2TB SSD WiFi 6 "
            "BT5.2 4K HD Mini PC for Gamer",
        ),
        feed_id="47215",
    )

    feed = FeedServiceFake(
        {
            "47215": [
                primeiro,
                segundo,
            ],
        }
    )

    scraper = AliExpressScraper(
        feed_service=feed,
        preco_service=PrecoServiceFake({}),
        feed_ids=("47215",),
        itens_por_feed=10,
        candidatos_por_feed=10,
        max_validacoes=5,
        deslocamento_feed=0,
    )

    candidatos = scraper._buscar_candidatos()

    ids = {candidato.produto.merchant_product_id for candidato in candidatos}

    assert len(ids) == 1


def test_diversidade_segura_terceiro_mini_pc():
    itens = [
        replace(
            produto("9201", "Mini PC Intel Core i9 " "16GB DDR4 2TB SSD Gaming"),
            feed_id="47215",
        ),
        replace(
            produto("9202", "Mini PC Intel Core N150 " "16GB DDR4 1TB SSD Office"),
            feed_id="47215",
        ),
        replace(
            produto("9203", "Mini PC Intel Core i3 " "8GB DDR4 512GB SSD Home"),
            feed_id="47215",
        ),
        replace(
            produto("9204", "Nubia Z70 Ultra 5G " "Smartphone Snapdragon 8 Elite"),
            feed_id="47215",
        ),
    ]

    feed = FeedServiceFake(
        {
            "47215": itens,
        }
    )

    scraper = AliExpressScraper(
        feed_service=feed,
        preco_service=PrecoServiceFake({}),
        feed_ids=("47215",),
        itens_por_feed=10,
        candidatos_por_feed=10,
        max_validacoes=10,
        deslocamento_feed=0,
    )

    candidatos = scraper._buscar_candidatos()

    primeiras = [candidato.classificacao.categoria for candidato in candidatos[:3]]

    assert primeiras.count("Computador e Mini PC") <= 2

    assert "Celular" in primeiras


def test_inductance_tester_vira_maker():
    oferta = _oferta_para_classificar(
        "Type C Inductance Tester for Phones "
        "PCB Motherboard Repair Diagnostics "
        "Electromagnetic Non-Contact "
        "Fault Detection Tool"
    )

    resultado = ClassificadorProduto().classificar(oferta)

    assert resultado.eh_nicho is True

    assert resultado.categoria == "Maker e bancada"


def test_descarta_sku_de_128gb_quando_titulo_anuncia_2tb_ssd():
    item = produto(
        "9301",
        "Mini PC Intel Core i9 " "16GB DDR4 RAM 2TB SSD",
    )

    scraper, _, _ = criar_scraper(
        [item],
        {
            "9301": preco_valido(
                "9301",
                principal=1072.68,
                normal=2437.90,
                promocional=1072.68,
                sku_atributo=("14:10#PL 128GB"),
            )
        },
    )

    assert scraper.buscar_ofertas(limite=1) == []


def test_aceita_sku_2048gb_quando_titulo_anuncia_2tb_ssd():
    item = produto(
        "9302",
        "Mini PC Intel Core i9 " "16GB DDR4 RAM 2TB SSD",
    )

    scraper, _, _ = criar_scraper(
        [item],
        {
            "9302": preco_valido(
                "9302",
                principal=1800.00,
                normal=2400.00,
                promocional=1800.00,
                sku_atributo=("14:193#PL 2048GB"),
            )
        },
    )

    ofertas = scraper.buscar_ofertas(limite=1)

    assert len(ofertas) == 1


def test_aceita_sku_1tb_quando_titulo_anuncia_1_ou_2tb_ssd():
    item = produto(
        "9303",
        "Mini PC Intel Core N150 " "16GB RAM 1/2TB SSD",
    )

    scraper, _, _ = criar_scraper(
        [item],
        {
            "9303": preco_valido(
                "9303",
                principal=1200.00,
                sku_atributo=("14:175#PL 1024GB"),
            )
        },
    )

    ofertas = scraper.buscar_ofertas(limite=1)

    assert len(ofertas) == 1


def test_sku_sem_capacidade_comparavel_continua_valido():
    item = produto(
        "9304",
        "Mini Electric Screwdriver Set " "30 in 1 Precision Repair Tools",
    )

    scraper, _, _ = criar_scraper(
        [item],
        {
            "9304": preco_valido(
                "9304",
                principal=96.89,
                sku_atributo=("14:193#30 in 1"),
            )
        },
    )

    ofertas = scraper.buscar_ofertas(limite=1)

    assert len(ofertas) == 1


def test_cooling_fan_nao_vira_notebook():
    oferta = _oferta_para_classificar(
        "New Original Laptop Notebook CPU " "Cooling Fan For Lenovo ThinkPad"
    )

    resultado = ClassificadorProduto().classificar(oferta)

    assert resultado.categoria == "Refrigera??o de PC"


def test_cpu_cooler_nao_vira_processador():
    oferta = _oferta_para_classificar(
        "CPU Cooler 4Pin PWM CPU Processor " "Cooler For Intel LGA1700 AMD AM4"
    )

    resultado = ClassificadorProduto().classificar(oferta)

    assert resultado.categoria == "Refrigera??o de PC"
