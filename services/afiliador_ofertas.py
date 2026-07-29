from models.oferta import Oferta
from repositories.links_afiliados_mercado_livre_repository import (
    LinksAfiliadosMercadoLivreRepository,
)
from services.identificador_mercado_livre import (
    IdentificadorMercadoLivre,
)


class AfiliadorOfertas:

    def __init__(self) -> None:

        self.identificador_ml = IdentificadorMercadoLivre()

        self.catalogo_ml = LinksAfiliadosMercadoLivreRepository()

    def afiliar(
        self,
        oferta: Oferta,
    ) -> Oferta:

        resultado = self.identificador_ml.identificar(oferta.link)

        if resultado.id_anuncio is None:
            return oferta

        oferta.marketplace = "mercado_livre"
        oferta.id_produto = resultado.id_produto
        oferta.id_anuncio = resultado.id_anuncio

        link_afiliado = self.catalogo_ml.obter_link_afiliado(oferta.link)

        if link_afiliado is None:

            oferta.pendente_afiliacao = True

            return oferta

        oferta.link_afiliado = link_afiliado

        oferta.link = link_afiliado

        oferta.pendente_afiliacao = False

        return oferta
