from filters.resultado_filtro import ResultadoFiltro
from models.oferta import Oferta


class OfertaFilter:

    def __init__(
        self,
        desconto_minimo: float,
        preco_maximo: float,
        relevancia_nicho_minima: float = 55
    ) -> None:
        self.desconto_minimo = desconto_minimo
        self.preco_maximo = preco_maximo
        self.relevancia_nicho_minima = (
            relevancia_nicho_minima
        )

    def analisar(
        self,
        oferta: Oferta
    ) -> ResultadoFiltro:
        if not oferta.eh_nicho:
            return ResultadoFiltro(
                aprovada=False,
                motivo=(
                    "Oferta não pertence ao nicho de "
                    "hardware e produtos gamer."
                )
            )

        if (
            oferta.relevancia_nicho
            < self.relevancia_nicho_minima
        ):
            return ResultadoFiltro(
                aprovada=False,
                motivo=(
                    "Relevância para o nicho abaixo "
                    "do mínimo: "
                    f"{oferta.relevancia_nicho:.2f} "
                    f"< {self.relevancia_nicho_minima:.2f}."
                )
            )

        if oferta.preco <= 0:
            return ResultadoFiltro(
                aprovada=False,
                motivo="O preço atual precisa ser maior que zero."
            )

        if oferta.preco > self.preco_maximo:
            return ResultadoFiltro(
                aprovada=False,
                motivo=(
                    f"Preço acima do máximo permitido: "
                    f"{oferta.moeda} {oferta.preco:.2f} "
                    f"> {oferta.moeda} "
                    f"{self.preco_maximo:.2f}."
                )
            )

        desconto = oferta.desconto_percentual

        if desconto < self.desconto_minimo:
            return ResultadoFiltro(
                aprovada=False,
                motivo=(
                    f"Desconto abaixo do mínimo: "
                    f"{desconto:.2f}% "
                    f"< {self.desconto_minimo:.2f}%."
                )
            )

        return ResultadoFiltro(
            aprovada=True,
            motivo=(
                "Oferta aprovada pelos critérios de nicho, "
                "preço e desconto."
            )
        )