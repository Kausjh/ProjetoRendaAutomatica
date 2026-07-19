from dataclasses import dataclass


@dataclass
class Oferta:
    nome: str
    loja: str
    preco: float
    preco_antigo: float | None
    link: str
    imagem: str | None
    moeda: str = "R$"

    # Monetização
    marketplace: str | None = None
    id_produto: str | None = None
    id_anuncio: str | None = None
    link_afiliado: str | None = None
    pendente_afiliacao: bool = False

    @property
    def desconto_percentual(self) -> float:
        if self.preco_antigo is None:
            return 0.0

        if self.preco_antigo <= 0:
            return 0.0

        if self.preco < 0:
            return 0.0

        if self.preco >= self.preco_antigo:
            return 0.0

        desconto = (
            (self.preco_antigo - self.preco)
            / self.preco_antigo
        ) * 100

        return desconto