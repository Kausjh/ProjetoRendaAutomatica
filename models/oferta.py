from dataclasses import dataclass, field


@dataclass
class Oferta:
    nome: str
    loja: str
    preco: float
    preco_antigo: float | None
    link: str
    imagem: str | None
    moeda: str = "R$"

    # Dados comerciais extraídos da loja
    desconto_anunciado: float | None = None

    # Validação
    valida: bool = True
    motivos_validacao: list[str] = field(default_factory=list)

    # Monetização
    marketplace: str | None = None
    id_produto: str | None = None
    id_anuncio: str | None = None
    link_afiliado: str | None = None
    pendente_afiliacao: bool = False

    # Classificação de nicho
    eh_nicho: bool = False
    categoria: str | None = None
    relevancia_nicho: float = 0.0
    termos_nicho: list[str] = field(default_factory=list)
    motivo_classificacao: str = ""

    # Curadoria comercial
    marca: str | None = None
    nota_comercial: float = 0.0
    motivos_comerciais: list[str] = field(default_factory=list)

    # Pontuação
    nota_tecnica: float = 0.0
    nota_historica: float = 0.0
    nota_final: float = 0.0

    @property
    def desconto_percentual(self) -> float:
        if self.preco_antigo is None:
            return 0.0

        if self.preco_antigo <= 0:
            return 0.0

        if self.preco <= 0:
            return 0.0

        if self.preco >= self.preco_antigo:
            return 0.0

        desconto = ((self.preco_antigo - self.preco) / self.preco_antigo) * 100

        return round(desconto, 2)
