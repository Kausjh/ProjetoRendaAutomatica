from models.oferta import Oferta
from services.pipeline.etapas.etapa_afiliacao import (
    EtapaAfiliacao,
)
from services.pipeline.pipeline import Pipeline


def main():

    oferta = Oferta(
        nome="Produto de Teste",
        loja="Mercado Livre",
        preco=199.90,
        preco_antigo=299.90,
        link="https://produto.mercadolivre.com.br/MLB-123456789-produto",
        imagem=None,
    )

    pipeline = Pipeline(
        EtapaAfiliacao(),
    )

    resultado = pipeline.executar(oferta)

    print()
    print("=" * 50)
    print("Resultado do Pipeline")
    print("=" * 50)
    print()

    print(f"Marketplace : {resultado.marketplace}")

    print(f"Produto     : {resultado.id_produto}")

    print(f"Anúncio     : {resultado.id_anuncio}")

    print(f"Pendente    : {resultado.pendente_afiliacao}")

    print(f"Link        : {resultado.link_afiliado}")


if __name__ == "__main__":
    main()
