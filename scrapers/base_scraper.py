from abc import ABC, abstractmethod

from models.oferta import Oferta


class BaseScraper(ABC):

    @abstractmethod
    def buscar_ofertas(self, limite: int = 5) -> list[Oferta]:
        """
        Retorna uma lista de ofertas.
        """
        pass
