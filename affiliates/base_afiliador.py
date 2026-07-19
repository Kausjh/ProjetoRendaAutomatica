from abc import ABC, abstractmethod


class BaseAfiliador(ABC):

    @property
    @abstractmethod
    def nome(self) -> str:
        """
        Retorna o nome público do afiliador.

        Esse nome será utilizado em logs, relatórios
        e métricas da aplicação.
        """
        raise NotImplementedError

    @abstractmethod
    def suporta(
        self,
        link: str
    ) -> bool:
        """
        Informa se o afiliador consegue processar o link.
        """
        raise NotImplementedError

    @abstractmethod
    def gerar_link(
        self,
        link_original: str
    ) -> str:
        """
        Gera o link que será utilizado na publicação.
        """
        raise NotImplementedError