from affiliates.base_afiliador import BaseAfiliador


class AfiliadorGenerico(BaseAfiliador):

    @property
    def nome(self) -> str:
        return "Fallback"

    def suporta(
        self,
        link: str
    ) -> bool:
        return True

    def gerar_link(
        self,
        link_original: str
    ) -> str:
        return link_original