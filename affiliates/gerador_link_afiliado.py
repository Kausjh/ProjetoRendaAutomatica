import logging

from affiliates.base_afiliador import BaseAfiliador
from affiliates.resultado_link_afiliado import (
    ResultadoLinkAfiliado,
)

logger = logging.getLogger(__name__)

# 63.8738, -149.7525


class GeradorLinkAfiliado:

    def __init__(self) -> None:
        self.afiliadores: list[BaseAfiliador] = []

    def registrar(
        self,
        afiliador: BaseAfiliador,
    ) -> None:
        self.afiliadores.append(afiliador)

    def gerar(
        self,
        link_original: str,
    ) -> ResultadoLinkAfiliado:
        for afiliador in self.afiliadores:
            try:
                suporta_link = afiliador.suporta(link_original)

            except Exception:
                logger.exception(
                    "Falha ao verificar se o afiliador '%s' " "suporta o link: %s",
                    afiliador.nome,
                    link_original,
                )

                continue

            if not suporta_link:
                continue

            try:
                link_publicacao = afiliador.gerar_link(link_original)

            except Exception:
                logger.exception(
                    "Falha ao gerar link com o afiliador '%s'. " "O link original será mantido: %s",
                    afiliador.nome,
                    link_original,
                )

                link_publicacao = link_original

            if not isinstance(link_publicacao, str) or not link_publicacao.strip():
                logger.warning(
                    "O afiliador '%s' retornou um link inválido. "
                    "O link original será mantido: %s",
                    afiliador.nome,
                    link_original,
                )

                link_publicacao = link_original

            link_publicacao = link_publicacao.strip()

            return ResultadoLinkAfiliado(
                link_original=link_original,
                link_publicacao=link_publicacao,
                afiliador_utilizado=afiliador.nome,
                foi_transformado=(link_publicacao != link_original),
            )

        return ResultadoLinkAfiliado(
            link_original=link_original,
            link_publicacao=link_original,
            afiliador_utilizado="Nenhum",
            foi_transformado=False,
        )
