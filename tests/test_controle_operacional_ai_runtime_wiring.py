from __future__ import annotations

import ast
import inspect
from pathlib import Path

from services.classificador_produto_assistido_ai import (
    ClassificadorProdutoAssistidoAI,
)
from services.controle_operacional_ai import (
    ControleOperacionalInteligenciaAI,
)
from services.curadoria_publicacao_assistida_ai import (
    CuradoriaPublicacaoAssistidaAI,
)


def test_consumidores_aceitam_controle_operacional_opcional():
    assert "controle_operacional" in inspect.signature(ClassificadorProdutoAssistidoAI).parameters

    assert "controle_operacional" in inspect.signature(CuradoriaPublicacaoAssistidaAI).parameters


def test_consumidores_preservam_none_por_padrao():
    assert ClassificadorProdutoAssistidoAI().controle_operacional is None

    assert CuradoriaPublicacaoAssistidaAI().controle_operacional is None


def test_consumidores_preservam_mesma_instancia():
    controle = ControleOperacionalInteligenciaAI()

    classificador = ClassificadorProdutoAssistidoAI(
        habilitado=False,
        controle_operacional=controle,
    )

    curadoria = CuradoriaPublicacaoAssistidaAI(
        habilitado=False,
        controle_operacional=controle,
    )

    assert classificador.controle_operacional is controle

    assert curadoria.controle_operacional is controle


def test_main_cria_um_unico_controle_e_compartilha():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    main = next(
        node
        for node in arvore.body
        if (
            isinstance(
                node,
                ast.AsyncFunctionDef,
            )
            and node.name == "main"
        )
    )

    criacoes = [
        node
        for node in ast.walk(main)
        if (
            isinstance(
                node,
                ast.Call,
            )
            and isinstance(
                node.func,
                ast.Name,
            )
            and node.func.id == "ControleOperacionalInteligenciaAI"
        )
    ]

    assert len(criacoes) == 1

    assignments = {
        node.targets[0].id: node.value
        for node in main.body
        if (
            isinstance(
                node,
                ast.Assign,
            )
            and len(node.targets) == 1
            and isinstance(
                node.targets[0],
                ast.Name,
            )
        )
    }

    for nome in (
        "classificador",
        "curadoria_publicacao",
    ):
        chamada = assignments[nome]

        kwargs = {keyword.arg: keyword.value for keyword in chamada.keywords}

        habilitado = kwargs["habilitado"]

        assert isinstance(
            habilitado,
            ast.Constant,
        )

        assert habilitado.value is False

        controle = kwargs["controle_operacional"]

        assert isinstance(
            controle,
            ast.Name,
        )

        assert controle.id == "controle_operacional_ai"


def test_consumidores_repassam_controle_ao_orquestrador():
    for caminho in (
        "services/classificador_produto_assistido_ai.py",
        "services/curadoria_publicacao_assistida_ai.py",
    ):
        texto = Path(caminho).read_text(encoding="utf-8-sig")

        arvore = ast.parse(texto)

        chamadas = [
            node
            for node in ast.walk(arvore)
            if (
                isinstance(
                    node,
                    ast.Call,
                )
                and isinstance(
                    node.func,
                    ast.Name,
                )
                and node.func.id == "interpretar_com_inteligencia_assistiva"
            )
        ]

        assert len(chamadas) == 1

        kwargs = {keyword.arg: keyword.value for keyword in chamadas[0].keywords}

        controle = kwargs["controle_operacional"]

        assert isinstance(
            controle,
            ast.Attribute,
        )

        assert controle.attr == "controle_operacional"


def test_main_nao_configura_provider_endpoint_ou_key():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    for proibido in (
        "ProvedorHttpInteligenciaAI",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
    ):
        assert proibido not in texto


# 63.8738, -149.7525
