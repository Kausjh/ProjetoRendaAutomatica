from models.oferta import Oferta
from repositories.links_afiliados_mercado_livre_repository import (
    LinksAfiliadosMercadoLivreRepository,
)
from repositories.pendencias_afiliacao_repository import (
    PendenciasAfiliacaoRepository,
)
from services.afiliadores.base_afiliador import (
    BaseAfiliador,
)
from services.identificador_mercado_livre import (
    IdentificadorMercadoLivre,
)


class AfiliadorMercadoLivre(BaseAfiliador):

    def __init__(self) -> None:

        self.identificador = IdentificadorMercadoLivre()

        self.catalogo = LinksAfiliadosMercadoLivreRepository()

        self.pendencias = PendenciasAfiliacaoRepository()

    def consegue_afiliar(
        self,
        oferta: Oferta,
    ) -> bool:

        resultado = self.identificador.identificar(oferta.link)

        return resultado.id_anuncio is not None

    def afiliar(
        self,
        oferta: Oferta,
    ) -> Oferta:

        resultado = self.identificador.identificar(oferta.link)

        oferta.marketplace = "mercado_livre"
        oferta.id_produto = resultado.id_produto
        oferta.id_anuncio = resultado.id_anuncio

        link_afiliado = self.catalogo.obter_link_afiliado(oferta.link)

        if link_afiliado is None:

            oferta.pendente_afiliacao = True

            self.pendencias.registrar(oferta)

            return oferta

        oferta.link_afiliado = link_afiliado

        oferta.link = link_afiliado

        oferta.pendente_afiliacao = False

        return oferta
