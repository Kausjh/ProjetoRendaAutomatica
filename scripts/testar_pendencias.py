from models.oferta import Oferta
from repositories.pendencias_afiliacao_repository import (
    PendenciasAfiliacaoRepository,
)
from services.afiliadores.afiliador_ofertas import (
    AfiliadorOfertas,
)


def main():

    oferta = Oferta(
        nome="Produto de Teste",
        loja="Mercado Livre",
        preco=99.90,
        preco_antigo=149.90,
        link="https://produto.mercadolivre.com.br/MLB-123456789-produto-de-teste",
        imagem=None,
    )

    afiliador = AfiliadorOfertas()

    oferta = afiliador.afiliar(oferta)

    print()

    print("=" * 60)
    print("Resultado da afiliação")
    print("=" * 60)

    print(f"Marketplace: {oferta.marketplace}")
    print(f"Produto: {oferta.id_produto}")
    print(f"Anúncio: {oferta.id_anuncio}")
    print(f"Pendente: {oferta.pendente_afiliacao}")
    print(f"Link final: {oferta.link}")

    print()

    repositorio = PendenciasAfiliacaoRepository()

    print("=" * 60)
    print("Pendências registradas")
    print("=" * 60)

    for pendencia in repositorio.carregar():

        print()

        for chave, valor in pendencia.items():

            print(f"{chave}: {valor}")


if __name__ == "__main__":
    main()
