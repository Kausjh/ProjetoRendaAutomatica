from abc import ABC, abstractmethod

from models.oferta import Oferta


class BaseAfiliador(ABC):

    @abstractmethod
    def consegue_afiliar(
        self,
        oferta: Oferta,
    ) -> bool: ...

    @abstractmethod
    def afiliar(
        self,
        oferta: Oferta,
    ) -> Oferta: ...
