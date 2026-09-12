from __future__ import annotations

import ast
from pathlib import Path

import pytest

from models.oferta import Oferta
from services.classificador_produto import (
    ClassificadorProduto,
)
from services.classificador_produto_assistido_ai import (
    ClassificadorProdutoAssistidoAI,
)


def _oferta(
    nome: str,
) -> Oferta:
    return Oferta(
        nome=nome,
        loja="Teste",
        preco=999.90,
        preco_antigo=None,
        link="https://example.com/produto",
        imagem=None,
        marketplace="teste",
    )


@pytest.mark.parametrize(
    "nome",
    [
        "AMD Ryzen 7 5700X",
        ("Notebook Gamer Acer Nitro V15 " "Ryzen 7 RTX 4060 16GB SSD NVMe"),
        "Kingston SSD NVMe Ryzen",
        "Ryzen NVMe",
        "Produto Misterioso XPTO 123",
        "Camiseta Gamer RTX 5090 NVIDIA",
    ],
)
def test_ai_desligada_preserva_classificacao_deterministica(
    nome,
):
    base = ClassificadorProduto().classificar(_oferta(nome))

    assistido = ClassificadorProdutoAssistidoAI(habilitado=False).classificar(_oferta(nome))

    assert assistido.eh_nicho == base.eh_nicho

    assert assistido.categoria == base.categoria

    assert assistido.relevancia == base.relevancia

    assert assistido.termos_encontrados == base.termos_encontrados

    assert assistido.motivo == base.motivo

    assert assistido.classificacao_final == base

    assert assistido.classificacao_deterministica == base


def test_resultado_assistido_expoe_interface_do_resultado_original():
    resultado = ClassificadorProdutoAssistidoAI(habilitado=False).classificar(_oferta("Ryzen NVMe"))

    assert isinstance(
        resultado.eh_nicho,
        bool,
    )

    assert resultado.categoria == resultado.classificacao_final.categoria

    assert resultado.relevancia == resultado.classificacao_final.relevancia

    assert resultado.termos_encontrados == resultado.classificacao_final.termos_encontrados

    assert resultado.motivo == resultado.classificacao_final.motivo


def test_aplicar_classificacao_ai_desligada_preserva_oferta():
    nome = "Ryzen NVMe"

    oferta_base = _oferta(nome)

    oferta_assistida = _oferta(nome)

    resultado_base = ClassificadorProduto().aplicar_classificacao(oferta_base)

    resultado_assistido = ClassificadorProdutoAssistidoAI(habilitado=False).aplicar_classificacao(
        oferta_assistida
    )

    assert resultado_assistido.eh_nicho == resultado_base.eh_nicho

    assert resultado_assistido.categoria == resultado_base.categoria

    assert resultado_assistido.relevancia == resultado_base.relevancia

    assert resultado_assistido.motivo == resultado_base.motivo

    assert oferta_assistida.eh_nicho == oferta_base.eh_nicho

    assert oferta_assistida.categoria == oferta_base.categoria

    assert oferta_assistida.relevancia_nicho == oferta_base.relevancia_nicho

    assert oferta_assistida.termos_nicho == oferta_base.termos_nicho

    assert oferta_assistida.motivo_classificacao == oferta_base.motivo_classificacao


def test_empate_real_com_ai_desligada_usa_fallback_sem_provider():
    resultado = ClassificadorProdutoAssistidoAI(habilitado=False).classificar(_oferta("Ryzen NVMe"))

    assert resultado.diagnostico.ambiguo is True

    assert resultado.gate_ai_acionado is True

    assert resultado.inteligencia_ai is not None

    assert resultado.inteligencia_ai.status == "desabilitado"

    assert resultado.inteligencia_ai.fallback_usado is True

    assert resultado.classificacao_final == resultado.classificacao_deterministica


def test_main_usa_classificador_assistido_com_ai_desligada():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    import_assistido = False

    atribuicoes_classificador = []

    coletor_recebe_classificador = False

    for node in ast.walk(arvore):
        if isinstance(
            node,
            ast.ImportFrom,
        ):
            if node.module == ("services." "classificador_produto_assistido_ai"):
                nomes = {alias.name for alias in node.names}

                if "ClassificadorProdutoAssistidoAI" in nomes:
                    import_assistido = True

        if isinstance(
            node,
            ast.Assign,
        ):
            if (
                len(node.targets) == 1
                and isinstance(
                    node.targets[0],
                    ast.Name,
                )
                and node.targets[0].id == "classificador"
            ):
                atribuicoes_classificador.append(node.value)

        if isinstance(
            node,
            ast.Call,
        ):
            if (
                isinstance(
                    node.func,
                    ast.Name,
                )
                and node.func.id == "ColetorOfertas"
            ):
                for keyword in node.keywords:
                    if (
                        keyword.arg == "classificador"
                        and isinstance(
                            keyword.value,
                            ast.Name,
                        )
                        and keyword.value.id == "classificador"
                    ):
                        coletor_recebe_classificador = True

    assert import_assistido is True

    assert len(atribuicoes_classificador) == 1

    criacao = atribuicoes_classificador[0]

    assert isinstance(
        criacao,
        ast.Call,
    )

    assert isinstance(
        criacao.func,
        ast.Name,
    )

    assert criacao.func.id == "ClassificadorProdutoAssistidoAI"

    habilitado = [keyword for keyword in criacao.keywords if keyword.arg == "habilitado"]

    assert len(habilitado) == 1

    assert isinstance(
        habilitado[0].value,
        ast.Constant,
    )

    assert habilitado[0].value.value is False

    assert coletor_recebe_classificador is True


def test_main_nao_configura_provider_endpoint_ou_api_key():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    assert "ProvedorHttpInteligenciaAI" not in texto

    assert "OPENAI_API_KEY" not in texto

    assert "ANTHROPIC_API_KEY" not in texto

    assert "GEMINI_API_KEY" not in texto


def test_coletor_continua_recebendo_objeto_com_interface_esperada():
    classificador = ClassificadorProdutoAssistidoAI(habilitado=False)

    resultado = classificador.aplicar_classificacao(_oferta("AMD Ryzen 7 5700X"))

    # Interface consumida hoje pelo ColetorOfertas.
    assert hasattr(
        resultado,
        "eh_nicho",
    )

    assert hasattr(
        resultado,
        "motivo",
    )

    assert hasattr(
        resultado,
        "categoria",
    )

    assert hasattr(
        resultado,
        "relevancia",
    )

    assert hasattr(
        resultado,
        "termos_encontrados",
    )
