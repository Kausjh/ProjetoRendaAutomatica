# 63.8738, -149.7525

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResultadoValidacaoPrecoSocialScout:
    status: str
    marketplace: str | None = None
    url: str | None = None

    titulo_oficial: str = ""

    preco_oficial: float | None = None
    preco_original_oficial: float | None = None
    tipo_preco_oficial: str | None = None

    preco_parcelado_oficial: float | None = None
    parcelas: int | None = None
    valor_parcela: float | None = None

    disponivel: bool | None = None
    preco_valido_ate: str | None = None

    preco_original_grupo: float | None = None
    preco_oferta_grupo: float | None = None
    preco_final_grupo: float | None = None

    codigo_cupom: str | None = None
    desconto_cupom_percentual: float | None = None

    preco_base_confere: bool = False
    preco_original_confere: bool | None = None

    preco_final_coerente_com_desconto: bool | None = None

    # IMPORTANTE:
    # coerencia matematica nao significa que o cupom
    # esteja ativo ou aplicavel na conta do comprador.
    cupom_validado: bool = False

    # Promotion Intelligence oficial do marketplace.
    #
    # Evidencia promocional != codigo de cupom validado.
    status_promocao_marketplace: str = "nao_consultada"
    promocao_marketplace_confirmada: bool = False
    tipo_promocao_marketplace: str | None = None

    preco_promocional_marketplace: float | None = None
    valor_desconto_promocional_marketplace: float | None = None
    desconto_promocional_marketplace_percentual: float | None = None

    preco_grupo_confere_promocao: bool | None = None

    fonte_promocao_marketplace: str | None = None
    motivo_promocao_marketplace: str = ""

    motivo: str = ""
