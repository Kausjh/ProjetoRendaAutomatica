from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXECUTOR = ROOT / "services" / "executor_pipeline.py"

REPO = ROOT / "repositories" / "fila_publicacao_repository.py"


def _arvore_executor():
    texto = EXECUTOR.read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

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
        texto,
        arvore,
        executar,
    )


def test_importa_agregador_publicacao():
    _, arvore, _ = _arvore_executor()

    imports = [
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.ImportFrom,
        )
        and node.module == ("services.scout." "feedback_publicacao_" "discovery_comercial_hunter")
    ]

    assert len(imports) == 1


def test_agregador_publicacao_e_chamado_uma_vez():
    _, _, executar = _arvore_executor()

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
        and node.func.id == ("criar_feedback_publicacao_" "discovery_comercial_hunter")
    ]

    assert len(chamadas) == 1


def test_runtime_busca_metodo_dedicado_do_repository():
    texto, _, _ = _arvore_executor()

    assert '"historico_publicacoes_discovery_comercial"' in texto

    assert "getattr(" in texto


def test_runtime_mantem_compatibilidade_com_repository_fake():
    texto, _, _ = _arvore_executor()

    assert "if callable(" in texto

    assert "historico_publicacoes_discovery = []" in texto


def test_relatorio_persiste_publication_outcome():
    _, _, executar = _arvore_executor()

    dicionarios = [
        node
        for node in ast.walk(executar)
        if isinstance(
            node,
            ast.Dict,
        )
    ]

    chaves = set()

    for dicionario in dicionarios:
        for chave in dicionario.keys:
            if isinstance(
                chave,
                ast.Constant,
            ) and isinstance(
                chave.value,
                str,
            ):
                chaves.add(chave.value)

    assert "commercial_discovery_publication_outcome" in chaves


def test_publication_outcome_nao_controla_decisoes():
    _, _, executar = _arvore_executor()

    nomes_proibidos = {
        "feedback_publicacao_discovery_comercial",
    }

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

        assert not (nomes & nomes_proibidos)


def test_historico_publicacoes_recentes_permanece_sem_proveniencia():
    texto = REPO.read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    classe = next(
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.ClassDef,
        )
        and node.name == "FilaPublicacaoRepository"
    )

    metodo = next(
        node
        for node in classe.body
        if isinstance(
            node,
            ast.FunctionDef,
        )
        and node.name == "historico_publicacoes_recentes"
    )

    linhas = texto.splitlines()

    trecho = "\n".join(linhas[metodo.lineno - 1 : metodo.end_lineno])

    assert "proveniencia_discovery_json" not in trecho

    assert "proveniencia_discovery_comercial" not in trecho
