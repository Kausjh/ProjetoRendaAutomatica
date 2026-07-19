import json
import tempfile
from pathlib import Path

from repositories.links_afiliados_mercado_livre_repository import (
    LinksAfiliadosMercadoLivreRepository
)
from services.identificador_mercado_livre import (
    IdentificadorMercadoLivre
)


LINK_ORIGINAL = (
    "https://www.mercadolivre.com.br/"
    "placa-de-video-nvidia-geforce-palit-"
    "rtx5060-8gb-infinity2-oc/p/MLB65407224"
    "?pdp_filters=item_id%3AMLB4577516683"
    "&matt_tool=38524122"
    "#origin=share"
    "&sid=share"
    "&wid=MLB4577516683"
    "&action=copy"
)

LINK_AFILIADO = "https://meli.la/TESTE123"


def executar_testes() -> None:
    identificador = IdentificadorMercadoLivre()

    print("=" * 80)
    print("TESTE 1 — EXTRAÇÃO DO CÓDIGO DO ANÚNCIO")

    resultado = identificador.identificar(
        LINK_ORIGINAL
    )

    print(f"Código do anúncio: {resultado.id_anuncio}")
    print(f"Código do produto: {resultado.id_produto}")

    assert resultado.id_anuncio == "MLB4577516683"
    assert resultado.id_produto == "MLB65407224"

    print("Resultado: aprovado")

    print("=" * 80)
    print("TESTE 2 — VALIDAÇÃO DO LINK AFILIADO")

    assert identificador.identificar(
        LINK_AFILIADO
    ).eh_link_afiliado

    assert not identificador.identificar(
        "https://mercadolivre.com.br/produto"
    ).eh_link_afiliado

    assert not identificador.identificar(
        "https://site-falso.com/meli.la/teste"
    ).eh_link_afiliado

    print("Resultado: aprovado")

    print("=" * 80)
    print("TESTE 3 — DOMÍNIO FALSO PARECIDO")

    link_falso = (
        "https://mercadolivre.com.br."
        "site-malicioso.com/"
        "MLB4577516683"
    )

    resultado = identificador.identificar(
        link_falso
    )

    assert resultado.id_anuncio is None

    print("Resultado: aprovado")

    print("=" * 80)
    print("TESTE 4 — CADASTRO E CONSULTA")

    with tempfile.TemporaryDirectory() as diretorio:
        caminho_catalogo = (
            Path(diretorio)
            / "links_afiliados.json"
        )

        repository = (
            LinksAfiliadosMercadoLivreRepository(
                caminho_arquivo=str(
                    caminho_catalogo
                )
            )
        )

        registro = repository.cadastrar(
            link_original=LINK_ORIGINAL,
            link_afiliado=LINK_AFILIADO
        )

        assert (
            registro.item_id
            == "MLB4577516683"
        )

        assert repository.quantidade() == 1

        por_link = repository.buscar_por_link(
            LINK_ORIGINAL
        )

        assert por_link is not None

        assert (
            por_link.link_afiliado
            == LINK_AFILIADO
        )

        por_codigo = repository.buscar_por_item_id(
            "MLB-4577516683"
        )

        assert por_codigo is not None

        assert (
            por_codigo.link_afiliado
            == LINK_AFILIADO
        )

        link_encontrado = (
            repository.obter_link_afiliado(
                LINK_ORIGINAL
            )
        )

        assert link_encontrado == LINK_AFILIADO

        print("Resultado: aprovado")

        print("=" * 80)
        print("TESTE 5 — ATUALIZAÇÃO SEM DUPLICAR")

        novo_link = "https://meli.la/NOVO123"

        repository.cadastrar(
            link_original=LINK_ORIGINAL,
            link_afiliado=novo_link
        )

        assert repository.quantidade() == 1

        atualizado = repository.buscar_por_item_id(
            "MLB4577516683"
        )

        assert atualizado is not None
        assert atualizado.link_afiliado == novo_link

        print("Resultado: aprovado")

        print("=" * 80)
        print("TESTE 6 — ARQUIVO JSON VÁLIDO")

        dados = json.loads(
            caminho_catalogo.read_text(
                encoding="utf-8"
            )
        )

        assert "MLB4577516683" in dados

        print("Resultado: aprovado")

    print("=" * 80)
    print("TODOS OS TESTES FORAM CONCLUÍDOS")
    print("Extração de anúncio: OK")
    print("Validação de link: OK")
    print("Proteção de domínio: OK")
    print("Cadastro: OK")
    print("Consulta: OK")
    print("Atualização: OK")
    print("=" * 80)


if __name__ == "__main__":
    executar_testes()