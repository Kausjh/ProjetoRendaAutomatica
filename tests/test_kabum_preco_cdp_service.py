# 63.8738, -149.7525

import json

from services.kabum_preco_cdp_service import (
    KabumPrecoCdpService,
)

ID = "699153"

URL = "https://www.kabum.com.br/" "produto/699153/monitor-teste"


def script(
    *,
    preco=649.99,
    moeda="BRL",
    disponibilidade=None,
):
    offer = {
        "@type": "Offer",
        "price": preco,
        "priceCurrency": moeda,
    }

    if disponibilidade is not None:
        offer["availability"] = disponibilidade

    return json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": "Monitor Gamer Teste",
            "offers": offer,
        }
    )


def test_jsonld_exato_com_preco_brl():
    resultado = KabumPrecoCdpService.analisar_jsonld(
        produto_id=ID,
        url_final=URL,
        scripts=[
            script(disponibilidade=("https://schema.org/" "InStock")),
        ],
    )

    assert resultado.valido is True
    assert resultado.preco_brl == 649.99
    assert resultado.titulo == "Monitor Gamer Teste"
    assert resultado.disponivel is True


def test_disponibilidade_ausente_nao_rejeita():
    resultado = KabumPrecoCdpService.analisar_jsonld(
        produto_id=ID,
        url_final=URL,
        scripts=[
            script(),
        ],
    )

    assert resultado.valido is True
    assert resultado.disponivel is None


def test_out_of_stock_explicito():
    resultado = KabumPrecoCdpService.analisar_jsonld(
        produto_id=ID,
        url_final=URL,
        scripts=[
            script(disponibilidade=("https://schema.org/" "OutOfStock")),
        ],
    )

    assert resultado.valido is True
    assert resultado.disponivel is False


def test_id_final_divergente_bloqueia():
    resultado = KabumPrecoCdpService.analisar_jsonld(
        produto_id=ID,
        url_final=("https://www.kabum.com.br/" "produto/999999/outro"),
        scripts=[
            script(),
        ],
    )

    assert resultado.valido is False

    assert resultado.motivo == "produto_kabum_redirecionado"


def test_moeda_nao_brl_bloqueia():
    resultado = KabumPrecoCdpService.analisar_jsonld(
        produto_id=ID,
        url_final=URL,
        scripts=[
            script(moeda="USD"),
        ],
    )

    assert resultado.valido is False

    assert resultado.motivo == "preco_kabum_brl_ausente"


def test_precos_distintos_sao_ambiguos():
    dados = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Produto Teste",
        "offers": [
            {
                "@type": "Offer",
                "price": 100.00,
                "priceCurrency": "BRL",
            },
            {
                "@type": "Offer",
                "price": 120.00,
                "priceCurrency": "BRL",
            },
        ],
    }

    resultado = KabumPrecoCdpService.analisar_jsonld(
        produto_id=ID,
        url_final=URL,
        scripts=[
            json.dumps(dados),
        ],
    )

    assert resultado.valido is False

    assert resultado.motivo == "precos_kabum_ambiguos"


# 63.8738, -149.7525


def test_cooldown_persistente_sobrevive_nova_instancia(
    tmp_path,
    monkeypatch,
):
    arquivo = tmp_path / "kabum_cooldown.txt"

    primeira = KabumPrecoCdpService(
        cooldown_desafio_segundos=1_800,
        arquivo_cooldown=arquivo,
    )

    primeira._ativar_cooldown_desafio()

    assert arquivo.is_file()
    assert primeira._em_cooldown_desafio() is True

    segunda = KabumPrecoCdpService(
        cooldown_desafio_segundos=1_800,
        arquivo_cooldown=arquivo,
    )

    def nao_pode_abrir_playwright():
        raise AssertionError("CDP nao pode ser acessado " "durante cooldown.")

    monkeypatch.setattr(
        ("services." "kabum_preco_cdp_service." "sync_playwright"),
        nao_pode_abrir_playwright,
    )

    resultado = segunda.validar(
        ID,
        URL,
    )

    assert resultado.valido is False

    assert resultado.motivo == segunda.MOTIVO_COOLDOWN


def test_cooldown_persistente_expirado_e_removido(
    tmp_path,
):
    arquivo = tmp_path / "kabum_cooldown.txt"

    arquivo.write_text(
        "1",
        encoding="utf-8",
    )

    service = KabumPrecoCdpService(
        arquivo_cooldown=arquivo,
    )

    assert service._em_cooldown_desafio() is False

    assert not arquivo.exists()
