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

    motivo: str = ""
