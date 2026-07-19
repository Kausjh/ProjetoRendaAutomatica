from abc import ABC, abstractmethod

from models.oferta import Oferta


class BaseEtapa(ABC):
    """
    Classe base para todas as etapas do Pipeline.

    Cada etapa recebe uma Oferta, pode alterá-la
    e devolve a própria Oferta para a próxima etapa.
    """

    @abstractmethod
    def executar(
        self,
        oferta: Oferta
    ) -> Oferta:
        """
        Executa a etapa do Pipeline.
        """
        raise NotImplementedError