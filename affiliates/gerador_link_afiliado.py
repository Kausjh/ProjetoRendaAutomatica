from affiliates.base_afiliador import BaseAfiliador
from affiliates.resultado_link_afiliado import (
    ResultadoLinkAfiliado
)


class GeradorLinkAfiliado:

    def __init__(self) -> None:
        self.afiliadores: list[BaseAfiliador] = []

    def registrar(
        self,
        afiliador: BaseAfiliador
    ) -> None:
        self.afiliadores.append(
            afiliador
        )

    def gerar(
        self,
        link_original: str
    ) -> ResultadoLinkAfiliado:
        for afiliador in self.afiliadores:
            if not afiliador.suporta(
                link_original
            ):
                continue

            link_publicacao = afiliador.gerar_link(
                link_original
            )

            return ResultadoLinkAfiliado(
                link_original=link_original,
                link_publicacao=link_publicacao,
                afiliador_utilizado=afiliador.nome,
                foi_transformado=(
                    link_publicacao != link_original
                )
            )

        return ResultadoLinkAfiliado(
            link_original=link_original,
            link_publicacao=link_original,
            afiliador_utilizado="Nenhum",
            foi_transformado=False
        )