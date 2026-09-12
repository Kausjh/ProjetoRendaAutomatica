from abc import ABC, abstractmethod
from urllib.parse import urlparse


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
    def suporta(self, link: str) -> bool:
        """
        Informa se o afiliador consegue processar o link.
        """
        raise NotImplementedError

    @abstractmethod
    def gerar_link(self, link_original: str) -> str:
        """
        Gera o link que será utilizado na publicação.
        """
        raise NotImplementedError

    def validar_link_gerado(
        self,
        link_original: str,
        link_publicacao: str,
    ) -> bool:
        """Valida a saída antes de considerá-la afiliação bem-sucedida."""
        if not isinstance(link_original, str) or not isinstance(
            link_publicacao,
            str,
        ):
            return False

        original = link_original.strip()
        publicacao = link_publicacao.strip()

        if not original or not publicacao or publicacao == original:
            return False

        parsed = urlparse(publicacao)

        return parsed.scheme == "https" and bool(parsed.hostname)
