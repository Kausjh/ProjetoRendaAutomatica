from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from models.resultado_validacao_preco_social_scout import (
    ResultadoValidacaoPrecoSocialScout,
)
from services.scout.enriquecedor_promocao_social_scout import (
    EnriquecedorPromocaoSocialScout,
)
from services.scout.interpretador_condicoes_promocionais import (
    interpretar_condicoes_promocionais,
)


def test_pix_por_tipo_preco():
    resultado = interpretar_condicoes_promocionais(
        tipo_preco_oficial="pix",
        preco_valido_ate=None,
        evidencia_oficial="",
    )
    assert resultado.pix is True


def test_pix_por_evidencia():
    resultado = interpretar_condicoes_promocionais(
        tipo_preco_oficial=None,
        preco_valido_ate=None,
        evidencia_oficial="R$ 899,90 no PIX",
    )
    assert resultado.pix is True


def test_app_only_conservador():
    positivo = interpretar_condicoes_promocionais(
        tipo_preco_oficial=None,
        preco_valido_ate=None,
        evidencia_oficial="Oferta exclusiva no app",
    )
    negativo = interpretar_condicoes_promocionais(
        tipo_preco_oficial=None,
        preco_valido_ate=None,
        evidencia_oficial="Baixe o aplicativo",
    )
    assert positivo.app_only is True
    assert negativo.app_only is False


def test_vip_explicito():
    positivo = interpretar_condicoes_promocionais(
        tipo_preco_oficial=None,
        preco_valido_ate=None,
        evidencia_oficial="Preco Cliente VIP",
    )
    negativo = interpretar_condicoes_promocionais(
        tipo_preco_oficial=None,
        preco_valido_ate=None,
        evidencia_oficial="Clientes selecionados",
    )
    assert positivo.vip is True
    assert negativo.vip is False


def test_minimo_compra():
    resultado = interpretar_condicoes_promocionais(
        tipo_preco_oficial=None,
        preco_valido_ate=None,
        evidencia_oficial=("Cupom em compras acima de R$ 1.200,00"),
    )
    assert resultado.valor_minimo_compra == 1200.0


def test_expiracao_prefere_preco_valido_ate():
    resultado = interpretar_condicoes_promocionais(
        tipo_preco_oficial=None,
        preco_valido_ate="2026-09-20T23:59:00-03:00",
        evidencia_oficial="Oferta valida ate 15/09",
    )
    assert resultado.expiracao == "2026-09-20T23:59:00-03:00"


def test_expiracao_por_evidencia():
    resultado = interpretar_condicoes_promocionais(
        tipo_preco_oficial=None,
        preco_valido_ate=None,
        evidencia_oficial=("Oferta valida ate 15/09/2026 as 23:59"),
    )
    assert resultado.expiracao == "15/09/2026 as 23:59"


class EngineFake:
    def __init__(self):
        self.fechado = False

    def inspecionar(self, **kwargs):
        return SimpleNamespace(
            status="confirmada",
            promocao_confirmada=True,
            tipo_promocao="cupom",
            preco_promocional=80.0,
            valor_desconto=20.0,
            desconto_percentual=20.0,
            preco_grupo_confere=True,
            fonte_url=("https://www.mercadolivre.com.br/p/MLB1"),
            motivo="teste",
            evidencia=(
                "Exclusivo no app Cliente VIP "
                "em compras acima de R$ 500,00 "
                "Oferta valida ate 30/09/2026"
            ),
        )

    def fechar(self):
        self.fechado = True


def test_enriquecedor_transporta_cinco_condicoes():
    engine = EngineFake()
    enriquecedor = EnriquecedorPromocaoSocialScout(promotion_engine=engine)
    validacao = ResultadoValidacaoPrecoSocialScout(
        status="validado",
        marketplace="mercado_livre",
        preco_oficial=100.0,
        tipo_preco_oficial="pix",
    )
    resultado = enriquecedor.aplicar(
        deteccao=SimpleNamespace(
            codigo_cupom="VIP20",
            preco_final=80.0,
            marketplace="mercado_livre",
        ),
        resolucao=SimpleNamespace(
            marketplace="mercado_livre",
            id_produto="MLB1",
            url_original="https://meli.la/abc",
            url_destino=("https://www.mercadolivre.com.br/p/MLB1"),
        ),
        validacao=validacao,
    )

    assert resultado.promocao_pix_marketplace is True
    assert resultado.promocao_app_only_marketplace is True
    assert resultado.promocao_vip_marketplace is True
    assert resultado.valor_minimo_compra_promocao_marketplace == 500.0
    assert resultado.expiracao_promocao_marketplace == "30/09/2026"
    assert "Cliente VIP" in resultado.evidencia_promocao_marketplace
    assert resultado.cupom_validado is False
    assert engine.fechado is True


def test_nao_ml_reaproveita_pix_e_expiracao():
    class EngineNaoPodeRodar:
        def inspecionar(self, **kwargs):
            raise AssertionError("Engine ML nao deveria rodar.")

    enriquecedor = EnriquecedorPromocaoSocialScout(promotion_engine=EngineNaoPodeRodar())
    validacao = ResultadoValidacaoPrecoSocialScout(
        status="validado",
        marketplace="shopee",
        preco_oficial=100.0,
        tipo_preco_oficial="pix",
        preco_valido_ate="2026-09-30",
    )
    resultado = enriquecedor.aplicar(
        deteccao=SimpleNamespace(
            codigo_cupom=None,
            preco_final=100.0,
            marketplace="shopee",
        ),
        resolucao=SimpleNamespace(
            marketplace="shopee",
            id_produto="1",
            url_original="https://shopee.com.br/x",
            url_destino="https://shopee.com.br/x",
        ),
        validacao=validacao,
    )

    assert resultado.promocao_pix_marketplace is True
    assert resultado.expiracao_promocao_marketplace == "2026-09-30"


def test_construtor_transporta_campos():
    fonte = Path("services/scout/construtor_oferta_social_scout.py").read_text(encoding="utf-8-sig")

    for campo in (
        "promocao_pix_marketplace",
        "promocao_app_only_marketplace",
        "promocao_vip_marketplace",
        "valor_minimo_compra_promocao_marketplace",
        "expiracao_promocao_marketplace",
    ):
        assert f"oferta.{campo}" in fonte


def test_preco_oficial_nao_e_substituido():
    fonte = Path("services/scout/construtor_oferta_social_scout.py").read_text(encoding="utf-8-sig")

    assert "preco=preco," in fonte
    assert "preco=validacao.preco_promocional_marketplace" not in fonte


# 63.8738, -149.7525
