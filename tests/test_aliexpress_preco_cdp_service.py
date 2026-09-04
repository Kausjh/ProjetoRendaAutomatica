import json

from services.aliexpress_preco_cdp_service import (
    AliExpressPrecoCdpService,
)


def criar_html(
    produto_id: str,
    preco: str,
    moeda: str = "BRL",
) -> str:
    dados = {
        "@context": "https://schema.org",
        "@type": "Product",
        "offers": {
            "@type": "Offer",
            "url": ("https://pt.aliexpress.com/" f"item/{produto_id}.html"),
            "priceCurrency": moeda,
            "price": preco,
        },
    }

    return '<script type="application/ld+json">' + json.dumps(dados) + "</script>"


def criar_pdp(
    produto_id: str,
    *,
    sale: str,
    normal: str | None = None,
    atmosfera: str | None = None,
    supplementary: str | None = None,
) -> str:
    if normal is None:
        normal = sale

    banner = {}

    if atmosfera is not None:
        banner["atmosphereCode"] = atmosfera

    if supplementary is not None:
        banner["targetSkuBanner"] = {"supplementaryText": (supplementary)}

    dados = {
        "data": {
            "result": {
                "PRICE": {
                    "productId": int(produto_id),
                    "selectedSkuId": (12000000000000001),
                    "targetSkuPriceInfo": {
                        "originalPrice": {
                            "currency": "BRL",
                            "value": normal,
                        },
                        "salePriceString": (
                            "R$"
                            + sale.replace(
                                ".",
                                ",",
                            )
                        ),
                    },
                },
                "PRICE_BANNER": banner,
                ("PERSONAL_INFORMATION_" "SECURITY"): {
                    "features": {
                        "newUser": True,
                    }
                },
            }
        }
    }

    return json.dumps(dados)


class RespostaFake:
    def __init__(
        self,
        texto: str,
    ) -> None:
        self.url = "https://acs.aliexpress.com/" "h5/" "mtop.aliexpress.pdp.pc.query/" "1.0/"

        self._texto = texto

    def text(self):
        return self._texto


class PaginaFake:
    def __init__(
        self,
        paginas: dict[
            str,
            dict[str, str | None],
        ],
    ) -> None:
        self.paginas = paginas

        self.url = "about:blank"

        self._html = ""

        self.gotos: list[str] = []

        self.esperas: list[int] = []

        self._listeners: dict[
            str,
            list,
        ] = {}

    def on(
        self,
        evento,
        callback,
    ):
        self._listeners.setdefault(
            evento,
            [],
        ).append(callback)

    def remove_listener(
        self,
        evento,
        callback,
    ):
        callbacks = self._listeners.get(
            evento,
            [],
        )

        if callback in callbacks:
            callbacks.remove(callback)

    def goto(
        self,
        url,
        wait_until,
        timeout,
    ):
        assert wait_until == ("domcontentloaded")

        assert timeout > 0

        self.gotos.append(url)

        self.url = url

        pagina = self.paginas.get(
            url,
            {},
        )

        self._html = str(
            pagina.get(
                "html",
                "",
            )
            or ""
        )

        pdp = pagina.get("pdp")

        if pdp is not None:
            resposta = RespostaFake(str(pdp))

            for callback in list(
                self._listeners.get(
                    "response",
                    [],
                )
            ):
                callback(resposta)

    def wait_for_timeout(
        self,
        milissegundos,
    ):
        self.esperas.append(milissegundos)

    def content(self):
        return self._html


def pagina_produto(
    produto_id: str,
    preco: str,
    *,
    normal: str | None = None,
    moeda: str = "BRL",
    atmosfera: str | None = None,
    supplementary: str | None = None,
) -> dict[str, str]:
    return {
        "html": criar_html(
            produto_id,
            preco,
            moeda=moeda,
        ),
        "pdp": criar_pdp(
            produto_id,
            sale=preco,
            normal=normal,
            atmosfera=atmosfera,
            supplementary=supplementary,
        ),
    }


def test_reutiliza_mesma_pagina_para_varios_produtos():
    ids = [
        "1005012134809286",
        "1005010455923134",
    ]

    url_a = "https://pt.aliexpress.com/" f"item/{ids[0]}.html"

    url_b = "https://pt.aliexpress.com/" f"item/{ids[1]}.html"

    pagina = PaginaFake(
        {
            url_a: pagina_produto(
                ids[0],
                "38.04",
            ),
            url_b: pagina_produto(
                ids[1],
                "75.08",
            ),
        }
    )

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
    )

    resultados = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=ids,
    )

    assert len(pagina.gotos) == 2

    assert resultados[ids[0]].valido is True

    assert resultados[ids[0]].preco == 38.04

    assert resultados[ids[1]].valido is True

    assert resultados[ids[1]].preco == 75.08


def test_falha_de_um_produto_nao_impede_proximo():
    produto_ruim = "1005000000000001"

    produto_bom = "1005012134809286"

    url_ruim = "https://pt.aliexpress.com/" f"item/{produto_ruim}.html"

    url_bom = "https://pt.aliexpress.com/" f"item/{produto_bom}.html"

    pagina = PaginaFake(
        {
            url_ruim: {
                "html": ("<html>" "sem json-ld" "</html>"),
                "pdp": criar_pdp(
                    produto_ruim,
                    sale="10.00",
                ),
            },
            url_bom: pagina_produto(
                produto_bom,
                "38.04",
            ),
        }
    )

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
    )

    resultados = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[
            produto_ruim,
            produto_bom,
        ],
    )

    assert resultados[produto_ruim].valido is False

    assert resultados[produto_bom].valido is True

    assert resultados[produto_bom].preco == 38.04


def test_rejeita_id_invalido_sem_navegar():
    pagina = PaginaFake({})

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
    )

    resultados = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[
            "abc",
        ],
    )

    assert resultados["abc"].valido is False

    assert pagina.gotos == []


def test_remove_ids_duplicados():
    produto_id = "1005012134809286"

    url = "https://pt.aliexpress.com/" f"item/{produto_id}.html"

    pagina = PaginaFake(
        {
            url: pagina_produto(
                produto_id,
                "38.04",
            ),
        }
    )

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
    )

    resultados = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[
            produto_id,
            produto_id,
            produto_id,
        ],
    )

    assert len(resultados) == 1

    assert len(pagina.gotos) == 1


def test_preserva_rejeicao_de_moeda_nao_brl():
    produto_id = "1005012134809286"

    url = "https://pt.aliexpress.com/" f"item/{produto_id}.html"

    pagina = PaginaFake(
        {
            url: pagina_produto(
                produto_id,
                "8.96",
                moeda="CNY",
            ),
        }
    )

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
    )

    resultado = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[
            produto_id,
        ],
    )[produto_id]

    assert resultado.valido is False

    assert resultado.preco is None


def test_novo_usuario_retorna_preco_normal_e_preserva_promocao():
    produto_id = "1005012134809286"

    url = "https://pt.aliexpress.com/" f"item/{produto_id}.html"

    pagina = PaginaFake(
        {
            url: pagina_produto(
                produto_id,
                "25.04",
                normal="40.04",
                atmosfera=("new_user_" "platform_allowance_atm"),
            ),
        }
    )

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
    )

    resultado = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[
            produto_id,
        ],
    )[produto_id]

    assert resultado.valido is True

    assert resultado.preco == 40.04

    assert resultado.preco_normal == 40.04

    assert resultado.preco_promocional == 25.04

    assert resultado.preco_novo_usuario == 25.04

    assert resultado.promocao_novo_usuario is True


def test_promocao_comum_mantem_preco_promocional_principal():
    produto_id = "1005006505347249"

    url = "https://pt.aliexpress.com/" f"item/{produto_id}.html"

    pagina = PaginaFake(
        {
            url: pagina_produto(
                produto_id,
                "9.51",
                normal="10.01",
                atmosfera=("girdle_aplus_big_sale"),
            ),
        }
    )

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
    )

    resultado = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[
            produto_id,
        ],
    )[produto_id]

    assert resultado.valido is True

    assert resultado.preco == 9.51

    assert resultado.preco_normal == 10.01

    assert resultado.preco_promocional == 9.51

    assert resultado.preco_novo_usuario is None

    assert resultado.promocao_novo_usuario is False


def test_listener_pdp_e_removido_apos_cada_produto():
    produto_id = "1005012134809286"

    url = "https://pt.aliexpress.com/" f"item/{produto_id}.html"

    pagina = PaginaFake(
        {
            url: pagina_produto(
                produto_id,
                "38.04",
            ),
        }
    )

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
    )

    service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[
            produto_id,
        ],
    )

    assert (
        pagina._listeners.get(
            "response",
            [],
        )
        == []
    )


def test_desafio_humano_interrompe_lote():
    primeiro = "1005000000000001"
    segundo = "1005000000000002"
    terceiro = "1005000000000003"

    url_primeiro = "https://pt.aliexpress.com/" f"item/{primeiro}.html"

    url_segundo = "https://pt.aliexpress.com/" f"item/{segundo}.html"

    url_terceiro = "https://pt.aliexpress.com/" f"item/{terceiro}.html"

    pagina = PaginaFake(
        {
            url_primeiro: {
                "html": ("<html><body>" "Please verify you are human" "</body></html>"),
                "pdp": None,
            },
            url_segundo: pagina_produto(
                segundo,
                "38.04",
            ),
            url_terceiro: pagina_produto(
                terceiro,
                "75.08",
            ),
        }
    )

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
    )

    resultados = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[
            primeiro,
            segundo,
            terceiro,
        ],
    )

    assert len(pagina.gotos) == 1

    assert resultados[primeiro].motivo == service.MOTIVO_DESAFIO

    assert resultados[segundo].motivo == service.MOTIVO_COOLDOWN

    assert resultados[terceiro].motivo == service.MOTIVO_COOLDOWN


def test_cooldown_impede_nova_navegacao():
    desafio = "1005000000000010"
    produto = "1005000000000011"

    url_desafio = "https://pt.aliexpress.com/" f"item/{desafio}.html"

    url_produto = "https://pt.aliexpress.com/" f"item/{produto}.html"

    pagina = PaginaFake(
        {
            url_desafio: {
                "html": ("<html><body>" "Human Verification" "</body></html>"),
                "pdp": None,
            },
            url_produto: pagina_produto(
                produto,
                "38.04",
            ),
        }
    )

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
    )

    primeiro = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[
            desafio,
        ],
    )

    assert primeiro[desafio].motivo == service.MOTIVO_DESAFIO

    quantidade_antes = len(pagina.gotos)

    segundo = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[
            produto,
        ],
    )

    assert len(pagina.gotos) == quantidade_antes

    assert segundo[produto].motivo == service.MOTIVO_COOLDOWN


def test_cooldown_persistente_sobrevive_nova_instancia(
    tmp_path,
):
    desafio = "1005000000000100"
    produto = "1005000000000101"

    url_desafio = "https://pt.aliexpress.com/" f"item/{desafio}.html"

    url_produto = "https://pt.aliexpress.com/" f"item/{produto}.html"

    arquivo_cooldown = tmp_path / "aliexpress_cooldown.txt"

    pagina_desafio = PaginaFake(
        {
            url_desafio: {
                "html": ("<html><body>" "Human Verification" "</body></html>"),
                "pdp": None,
            },
        }
    )

    primeira_instancia = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
        arquivo_cooldown=(arquivo_cooldown),
    )

    resultado_desafio = primeira_instancia.validar_produtos_com_pagina(
        pagina=pagina_desafio,
        produto_ids=[desafio],
    )

    assert resultado_desafio[desafio].motivo == primeira_instancia.MOTIVO_DESAFIO

    assert arquivo_cooldown.is_file()

    pagina_produto_valido = PaginaFake(
        {
            url_produto: pagina_produto(
                produto,
                "38.04",
            ),
        }
    )

    segunda_instancia = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
        arquivo_cooldown=(arquivo_cooldown),
    )

    resultado_cooldown = segunda_instancia.validar_produtos_com_pagina(
        pagina=pagina_produto_valido,
        produto_ids=[produto],
    )

    assert pagina_produto_valido.gotos == []

    assert resultado_cooldown[produto].motivo == segunda_instancia.MOTIVO_COOLDOWN


def test_cooldown_persistente_expirado_e_removido(
    tmp_path,
):
    produto = "1005000000000200"

    url_produto = "https://pt.aliexpress.com/" f"item/{produto}.html"

    arquivo_cooldown = tmp_path / "aliexpress_cooldown.txt"

    arquivo_cooldown.write_text(
        "1",
        encoding="utf-8",
    )

    pagina = PaginaFake(
        {
            url_produto: pagina_produto(
                produto,
                "38.04",
            ),
        }
    )

    service = AliExpressPrecoCdpService(
        espera_pos_carga_ms=0,
        arquivo_cooldown=(arquivo_cooldown),
    )

    resultado = service.validar_produtos_com_pagina(
        pagina=pagina,
        produto_ids=[produto],
    )

    assert resultado[produto].valido is True

    assert len(pagina.gotos) == 1

    assert not arquivo_cooldown.exists()
