# 63.8738, -149.7525

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

    # Dados comerciais extraidos da loja
    desconto_anunciado: float | None = None

    # Precos condicionais / dados da fonte
    preco_novo_usuario: float | None = None
    moeda_novo_usuario: str | None = None
    preco_origem: float | None = None
    moeda_origem: str | None = None

    # Validacao
    valida: bool = True
    motivos_validacao: list[str] = field(default_factory=list)

    # Monetizacao
    marketplace: str | None = None
    id_produto: str | None = None
    id_anuncio: str | None = None
    link_afiliado: str | None = None
    pendente_afiliacao: bool = False

    # Classificacao de nicho
    eh_nicho: bool = False
    categoria: str | None = None
    relevancia_nicho: float = 0.0
    termos_nicho: list[str] = field(default_factory=list)
    motivo_classificacao: str = ""

    # Curadoria comercial
    marca: str | None = None
    nota_comercial: float = 0.0
    motivos_comerciais: list[str] = field(default_factory=list)

    # Normalizacao / identidade canonica
    produto_canonico: str | None = None
    chave_produto_canonica: str | None = None
    modelo_produto: str | None = None
    confianca_normalizacao: float = 0.0

    # Inteligencia de produto
    nota_produto: float = 0.0
    confianca_produto: float = 0.0
    nivel_desejabilidade: str = "baixo"
    motivos_produto: list[str] = field(default_factory=list)

    # Sinal externo de descoberta / preco condicionado.
    # Nunca substitui Oferta.preco.
    origem_descoberta: str | None = None
    preco_condicional_observado: float | None = None
    codigo_cupom_observado: str | None = None
    cupom_validado_descoberta: bool = False
    status_sinal_preco: str = "sem_sinal"
    confianca_sinal_preco: float = 0.0
    economia_condicional_percentual: float = 0.0
    motivos_sinal_preco: list[str] = field(default_factory=list)

    # Familia semantica / anti-repost
    familia_produto: str | None = None
    chave_familia_produto: str | None = None
    confianca_familia: float = 0.0

    # Curadoria de publicacao
    curadoria_publicavel: bool = True
    nota_curadoria: float = 0.0
    motivos_curadoria: list[str] = field(default_factory=list)

    # Pontuacao
    nota_tecnica: float = 0.0
    nota_historica: float = 0.0
    nota_final: float = 0.0
    componentes_pontuacao: dict[str, float] = field(default_factory=dict)

    # Oportunidades especiais / anomalias de preco
    tipo_oportunidade: str = "normal"
    anomalia_preco: bool = False
    anomalia_publicavel: bool = False
    confianca_anomalia: float = 0.0
    queda_anomala_percentual: float = 0.0
    motivos_anomalia: list[str] = field(default_factory=list)

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

        desconto = (self.preco_antigo - self.preco) / self.preco_antigo * 100

        return round(desconto, 2)
