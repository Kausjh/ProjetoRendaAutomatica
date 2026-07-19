from services.identificador_mercado_livre import (
    IdentificadorMercadoLivre,
)


def testar_link_produto():

    identificador = (
        IdentificadorMercadoLivre()
    )

    resultado = (
        identificador.identificar(
            "https://produto.mercadolivre.com.br/MLB-123456789-produto"
        )
    )

    assert resultado.id_produto == "MLB123456789"
    assert resultado.id_anuncio is None
    assert resultado.eh_link_afiliado is False


def testar_link_afiliado():

    identificador = (
        IdentificadorMercadoLivre()
    )

    resultado = (
        identificador.identificar(
            "https://meli.la/ABCDE"
        )
    )

    assert resultado.eh_link_afiliado is True


def testar_item_id():

    identificador = (
        IdentificadorMercadoLivre()
    )

    resultado = (
        identificador.identificar(
            "https://www.mercadolivre.com.br/?item_id=MLB987654321"
        )
    )

    assert resultado.id_anuncio == "MLB987654321"


def testar_wid():

    identificador = (
        IdentificadorMercadoLivre()
    )

    resultado = (
        identificador.identificar(
            "https://www.mercadolivre.com.br/?wid=MLB111111111"
        )
    )

    assert resultado.id_anuncio == "MLB111111111"


def testar_normalizacao_hifen():

    identificador = (
        IdentificadorMercadoLivre()
    )

    resultado = (
        identificador.identificar(
            "https://produto.mercadolivre.com.br/MLB-123456789-produto"
        )
    )

    assert resultado.id_produto == "MLB123456789"


def testar_normalizacao_underline():

    identificador = (
        IdentificadorMercadoLivre()
    )

    resultado = (
        identificador.identificar(
            "https://produto.mercadolivre.com.br/MLB_123456789-produto"
        )
    )

    assert resultado.id_produto == "MLB123456789"


def main():

    testar_link_produto()
    testar_link_afiliado()
    testar_item_id()
    testar_wid()
    testar_normalizacao_hifen()
    testar_normalizacao_underline()

    print()
    print("=" * 50)
    print("Todos os testes do IdentificadorMercadoLivre passaram.")
    print("=" * 50)


if __name__ == "__main__":
    main()