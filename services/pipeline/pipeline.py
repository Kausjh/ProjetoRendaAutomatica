from models.oferta import Oferta
from services.pipeline.base_etapa import BaseEtapa


class Pipeline:

    def __init__(
        self,
        *etapas: BaseEtapa
    ) -> None:

        self.etapas = list(etapas)

    def adicionar_etapa(
        self,
        etapa: BaseEtapa
    ) -> None:

        self.etapas.append(etapa)

    def executar(
        self,
        oferta: Oferta
    ) -> Oferta:

        for etapa in self.etapas:

            oferta = etapa.executar(
                oferta
            )

        return oferta