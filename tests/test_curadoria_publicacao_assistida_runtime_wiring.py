from __future__ import annotations

import ast
from pathlib import Path

import pytest

from models.oferta import Oferta
from services.curadoria_publicacao import (
    CuradoriaPublicacao,
)
from services.curadoria_publicacao_assistida_ai import (
    CuradoriaPublicacaoAssistidaAI,
)


def criar_oferta(
    *,
    nome: str,
    categoria: str = "Placa de vídeo",
    preco: float = 2199.0,
    preco_antigo: float | None = None,
    relevancia: float = 90.0,
    confianca: float = 95.0,
) -> Oferta:
    oferta = Oferta(
        nome=nome,
        loja="Teste V19D2",
        preco=preco,
        preco_antigo=preco_antigo,
        link="https://example.com/v19d2",
        imagem=None,
        marketplace="teste",
    )

    oferta.categoria = categoria
    oferta.eh_nicho = True
    oferta.relevancia_nicho = relevancia
    oferta.confianca_normalizacao = confianca

    return oferta


@pytest.mark.parametrize(
    ("nome," "categoria," "preco," "preco_antigo," "relevancia," "confianca"),
    [
        (
            "Placa de Video RTX 4060 8GB GDDR6",
            "Placa de vídeo",
            2199.0,
            None,
            90.0,
            95.0,
        ),
        (
            "Placa de Video RTX 3060 ou RTX 4060 8GB",
            "Placa de vídeo",
            1999.0,
            None,
            90.0,
            95.0,
        ),
        (
            "Placa de Video RTX 4060 8GB GDDR6",
            "Placa de vídeo",
            2199.0,
            None,
            90.0,
            70.0,
        ),
        (
            "Placa de Video RTX 4060 8GB GDDR6",
            "Placa de vídeo",
            2199.0,
            None,
            70.0,
            95.0,
        ),
        (
            "Placa de Video RTX 4060 8GB GDDR6",
            "Placa de vídeo",
            2199.0,
            2199.0,
            90.0,
            95.0,
        ),
        (
            "SSD NVMe Kingston 1TB",
            "Armazenamento",
            399.0,
            None,
            90.0,
            95.0,
        ),
    ],
)
def test_ai_desligada_equivale_curadoria_deterministica(
    nome,
    categoria,
    preco,
    preco_antigo,
    relevancia,
    confianca,
):
    oferta_base = criar_oferta(
        nome=nome,
        categoria=categoria,
        preco=preco,
        preco_antigo=preco_antigo,
        relevancia=relevancia,
        confianca=confianca,
    )

    oferta_assistida = criar_oferta(
        nome=nome,
        categoria=categoria,
        preco=preco,
        preco_antigo=preco_antigo,
        relevancia=relevancia,
        confianca=confianca,
    )

    resultado_base = CuradoriaPublicacao(
        nota_minima=55.0,
        ativa=True,
    ).analisar(oferta_base)

    resultado_assistido = CuradoriaPublicacaoAssistidaAI(
        curadoria=CuradoriaPublicacao(
            nota_minima=55.0,
            ativa=True,
        ),
        habilitado=False,
    ).analisar(oferta_assistida)

    assert resultado_assistido.publicavel == resultado_base.publicavel

    assert resultado_assistido.nota == resultado_base.nota

    assert resultado_assistido.motivos == resultado_base.motivos

    assert resultado_assistido.bloqueios == resultado_base.bloqueios

    assert resultado_assistido.curadoria_final == resultado_base

    assert resultado_assistido.curadoria_deterministica == resultado_base

    assert oferta_assistida.curadoria_publicavel == oferta_base.curadoria_publicavel

    assert oferta_assistida.nota_curadoria == oferta_base.nota_curadoria

    assert oferta_assistida.motivos_curadoria == oferta_base.motivos_curadoria


def test_gate_assistivo_com_ai_desligada_usa_fallback():
    resultado = CuradoriaPublicacaoAssistidaAI(habilitado=False).analisar(
        criar_oferta(
            nome=("Placa de Video RTX 4060 " "8GB GDDR6"),
            confianca=70.0,
        )
    )

    assert resultado.publicavel is True
    assert resultado.gate_ai_acionado is True
    assert resultado.inteligencia_ai is not None

    assert resultado.inteligencia_ai.status == "desabilitado"

    assert resultado.inteligencia_ai.fallback_usado is True

    assert resultado.revisao_manual_sugerida is False

    assert resultado.curadoria_final == resultado.curadoria_deterministica


def test_reprovacao_deterministica_nao_abre_gate_ai():
    resultado = CuradoriaPublicacaoAssistidaAI(habilitado=False).analisar(
        criar_oferta(nome=("Placa de Video RTX 3060 " "ou RTX 4060 8GB"))
    )

    assert resultado.publicavel is False
    assert resultado.gate_ai_acionado is False
    assert resultado.inteligencia_ai is None
    assert resultado.revisao_manual_sugerida is False


def test_main_wiring_curadoria_assistida_ai_desligada():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    import_base = False
    import_assistida = False

    atribuicao_curadoria = None

    executor_recebe_curadoria = False

    for node in ast.walk(arvore):

        if isinstance(
            node,
            ast.ImportFrom,
        ):
            nomes = {alias.name for alias in node.names}

            if node.module == "services.curadoria_publicacao" and "CuradoriaPublicacao" in nomes:
                import_base = True

            if (
                node.module == ("services." "curadoria_publicacao_assistida_ai")
                and "CuradoriaPublicacaoAssistidaAI" in nomes
            ):
                import_assistida = True

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
                and node.targets[0].id == "curadoria_publicacao"
            ):
                atribuicao_curadoria = node.value

        if isinstance(
            node,
            ast.Call,
        ):
            if (
                isinstance(
                    node.func,
                    ast.Name,
                )
                and node.func.id == "ExecutorPipeline"
            ):
                for keyword in node.keywords:
                    if (
                        keyword.arg == "curadoria_publicacao"
                        and isinstance(
                            keyword.value,
                            ast.Name,
                        )
                        and keyword.value.id == "curadoria_publicacao"
                    ):
                        executor_recebe_curadoria = True

    assert import_base is True
    assert import_assistida is True

    assert isinstance(
        atribuicao_curadoria,
        ast.Call,
    )

    assert isinstance(
        atribuicao_curadoria.func,
        ast.Name,
    )

    assert atribuicao_curadoria.func.id == "CuradoriaPublicacaoAssistidaAI"

    kwargs = {keyword.arg: keyword.value for keyword in atribuicao_curadoria.keywords}

    assert set(kwargs) == {
        "curadoria",
        "habilitado",
    }

    assert isinstance(
        kwargs["habilitado"],
        ast.Constant,
    )

    assert kwargs["habilitado"].value is False

    base = kwargs["curadoria"]

    assert isinstance(
        base,
        ast.Call,
    )

    assert isinstance(
        base.func,
        ast.Name,
    )

    assert base.func.id == "CuradoriaPublicacao"

    base_kwargs = {keyword.arg: keyword.value for keyword in base.keywords}

    assert set(base_kwargs) == {
        "nota_minima",
        "ativa",
    }

    assert executor_recebe_curadoria is True


def test_main_preserva_configuracoes_reais_da_curadoria():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    assert "nota_minima=" "configuracoes.nota_minima_curadoria" in texto

    assert "ativa=" "configuracoes.curadoria_publicacao_ativa" in texto


def test_main_nao_configura_provider_endpoint_ou_api_key():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    proibidos = (
        "ProvedorHttpInteligenciaAI",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
    )

    for proibido in proibidos:
        assert proibido not in texto


def test_executor_pipeline_continua_ignorando_ai():
    texto = Path("services/executor_pipeline.py").read_text(encoding="utf-8-sig")

    proibidos = (
        "CuradoriaPublicacaoAssistidaAI",
        "revisao_manual_sugerida",
        "inteligencia_ai",
    )

    for proibido in proibidos:
        assert proibido not in texto


def test_interface_original_consumida_pelo_pipeline_permanece():
    resultado = CuradoriaPublicacaoAssistidaAI(habilitado=False).analisar(
        criar_oferta(nome=("Placa de Video RTX 4060 " "8GB GDDR6"))
    )

    assert hasattr(
        resultado,
        "publicavel",
    )

    assert hasattr(
        resultado,
        "nota",
    )

    assert hasattr(
        resultado,
        "motivos",
    )

    assert hasattr(
        resultado,
        "bloqueios",
    )
