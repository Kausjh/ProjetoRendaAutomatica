from models.oferta import Oferta

from services.afiliadores.afiliador_ofertas import (
    AfiliadorOfertas,
)

from services.pipeline.base_etapa import (
    BaseEtapa,
)


class EtapaAfiliacao(BaseEtapa):

    def __init__(self) -> None:

        self.afiliador = (
            AfiliadorOfertas()
        )

    def executar(
        self,
        oferta: Oferta
    ) -> Oferta:

        return self.afiliador.afiliar(
            oferta
        )