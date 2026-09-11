from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXECUTOR = ROOT / "services" / "executor_pipeline.py"


def _arvore_e_executar():
    arvore = ast.parse(EXECUTOR.read_text(encoding="utf-8-sig"))

    classe = next(
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.ClassDef,
        )
        and node.name == "ExecutorPipeline"
    )

    executar = next(
        node
        for node in classe.body
        if isinstance(
            node,
            ast.AsyncFunctionDef,
        )
        and node.name == "executar"
    )

    return (
        arvore,
        executar,
    )


def test_importa_criador_de_proveniencia():
    arvore, _ = _arvore_e_executar()

    imports = [
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.ImportFrom,
        )
        and node.module
        == ("services.scout." "proveniencia_publicacao_" "discovery_comercial_hunter")
    ]

    assert len(imports) == 1


def test_cria_mapa_de_proveniencia_uma_vez():
    _, executar = _arvore_e_executar()

    chamadas = [
        node
        for node in ast.walk(executar)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Name,
        )
        and node.func.id == ("criar_proveniencias_publicacao_" "discovery_comercial_hunter")
    ]

    assert len(chamadas) == 1


def test_criador_recebe_fila_final():
    _, executar = _arvore_e_executar()

    chamada = next(
        node
        for node in ast.walk(executar)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Name,
        )
        and node.func.id == ("criar_proveniencias_publicacao_" "discovery_comercial_hunter")
    )

    kwargs = {item.arg: item.value for item in chamada.keywords}

    assert set(kwargs) == {
        "observabilidade",
        "resultado_hunter",
        "ofertas_selecionadas_fila",
    }

    valor = kwargs["ofertas_selecionadas_fila"]

    nomes = {
        node.id
        for node in ast.walk(valor)
        if isinstance(
            node,
            ast.Name,
        )
    }

    assert "candidatos_fila" in nomes


def test_repository_recebe_proveniencia_depois_do_enqueue():
    _, executar = _arvore_e_executar()

    resultado_fila = next(
        node
        for node in ast.walk(executar)
        if isinstance(
            node,
            ast.Assign,
        )
        and any(
            isinstance(
                alvo,
                ast.Name,
            )
            and alvo.id == "resultado_fila"
            for alvo in node.targets
        )
    )

    chamadas_setter = [
        node
        for node in ast.walk(executar)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Attribute,
        )
        and node.func.attr == ("definir_proveniencia_" "discovery_comercial")
    ]

    assert len(chamadas_setter) == 1

    setter = chamadas_setter[0]

    assert setter.lineno > resultado_fila.end_lineno


def test_setter_usa_link_da_oferta_e_mapa():
    _, executar = _arvore_e_executar()

    setter = next(
        node
        for node in ast.walk(executar)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Attribute,
        )
        and node.func.attr == ("definir_proveniencia_" "discovery_comercial")
    )

    assert len(setter.args) == 2

    texto_args = [ast.unparse(argumento) for argumento in setter.args]

    assert texto_args[0] == "oferta.link"

    assert "proveniencias_publicacao_discovery" in texto_args[1]

    assert ".get(" in texto_args[1]


def test_proveniencia_nao_controla_decisoes():
    _, executar = _arvore_e_executar()

    for node in ast.walk(executar):
        if not isinstance(
            node,
            ast.If,
        ):
            continue

        nomes = {
            item.id
            for item in ast.walk(node.test)
            if isinstance(
                item,
                ast.Name,
            )
        }

        assert "proveniencias_publicacao_discovery" not in nomes
