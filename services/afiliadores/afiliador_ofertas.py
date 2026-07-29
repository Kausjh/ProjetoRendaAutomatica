from models.oferta import Oferta
from services.afiliadores.afiliador_mercado_livre import (
    AfiliadorMercadoLivre,
)


class AfiliadorOfertas:

    def __init__(self) -> None:

        self.afiliadores = [
            AfiliadorMercadoLivre(),
        ]

    def afiliar(
        self,
        oferta: Oferta,
    ) -> Oferta:

        for afiliador in self.afiliadores:

            if afiliador.consegue_afiliar(oferta):
                return afiliador.afiliar(oferta)

        return oferta
