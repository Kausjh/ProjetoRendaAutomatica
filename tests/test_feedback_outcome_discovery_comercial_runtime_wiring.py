# 63.8738, -149.7525

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXECUTOR = ROOT / "services" / "executor_pipeline.py"


def _arvore_e_executar():
    arvore = ast.parse(
        EXECUTOR.read_text(
            encoding="utf-8-sig",
        )
    )

    classes = [
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.ClassDef,
        )
        and node.name == "ExecutorPipeline"
    ]

    assert len(classes) == 1

    classe = classes[0]

    funcoes = [
        node
        for node in classe.body
        if isinstance(
            node,
            ast.AsyncFunctionDef,
        )
        and node.name == "executar"
    ]

    assert len(funcoes) == 1

    return (
        arvore,
        funcoes[0],
    )


def _chamada_feedback():
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
        and node.func.id == ("criar_feedback_outcome_" "discovery_comercial_hunter")
    ]

    assert len(chamadas) == 1

    return chamadas[0]


def test_importa_feedback():
    arvore, _ = _arvore_e_executar()

    imports = [
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.ImportFrom,
        )
        and node.module == ("services.scout." "feedback_outcome_" "discovery_comercial_hunter")
    ]

    assert len(imports) == 1


def test_chama_feedback_uma_vez():
    _chamada_feedback()


def test_feedback_recebe_quatro_entradas():
    chamada = _chamada_feedback()

    kwargs = {item.arg: item.value for item in chamada.keywords}

    assert set(kwargs) == {
        "observabilidade",
        "resultado_hunter",
        "ofertas_elegiveis",
        "ofertas_selecionadas_fila",
    }


def test_feedback_recebe_resultado_hunter():
    chamada = _chamada_feedback()

    kwargs = {item.arg: item.value for item in chamada.keywords}

    valor = kwargs["resultado_hunter"]

    assert isinstance(
        valor,
        ast.Call,
    )

    assert isinstance(
        valor.func,
        ast.Name,
    )

    assert valor.func.id == "getattr"


def test_feedback_recebe_elegiveis_reais():
    chamada = _chamada_feedback()

    kwargs = {item.arg: item.value for item in chamada.keywords}

    valor = kwargs["ofertas_elegiveis"]

    assert isinstance(
        valor,
        ast.GeneratorExp,
    )

    nomes = {
        node.id
        for node in ast.walk(valor)
        if isinstance(
            node,
            ast.Name,
        )
    }

    assert "ofertas_aprovadas" in nomes


def test_feedback_recebe_fila_final():
    chamada = _chamada_feedback()

    kwargs = {item.arg: item.value for item in chamada.keywords}

    valor = kwargs["ofertas_selecionadas_fila"]

    assert isinstance(
        valor,
        ast.GeneratorExp,
    )

    nomes = {
        node.id
        for node in ast.walk(valor)
        if isinstance(
            node,
            ast.Name,
        )
    }

    assert "candidatos_fila" in nomes


def test_feedback_antes_do_loop_da_fila():
    _, executar = _arvore_e_executar()

    atribuicoes = [
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
            and alvo.id == "feedback_discovery_comercial"
            for alvo in node.targets
        )
    ]

    assert len(atribuicoes) == 1

    loops_com_oferta = []

    for node in ast.walk(executar):
        if not isinstance(
            node,
            ast.For,
        ):
            continue

        if not (
            isinstance(
                node.iter,
                ast.Name,
            )
            and node.iter.id == "candidatos_fila"
        ):
            continue

        nomes = {
            item.id
            for item in ast.walk(node.target)
            if isinstance(
                item,
                ast.Name,
            )
        }

        if "oferta" in nomes:
            loops_com_oferta.append(node)

    assert len(loops_com_oferta) == 1

    assert atribuicoes[0].lineno < loops_com_oferta[0].lineno


def test_relatorio_persiste_outcome():
    _, executar = _arvore_e_executar()

    relatorios = [
        node.value
        for node in ast.walk(executar)
        if isinstance(
            node,
            ast.Assign,
        )
        and len(node.targets) == 1
        and isinstance(
            node.targets[0],
            ast.Name,
        )
        and node.targets[0].id == "relatorio"
        and isinstance(
            node.value,
            ast.Dict,
        )
    ]

    assert len(relatorios) == 1

    relatorio = relatorios[0]

    valores = {}

    for chave, valor in zip(
        relatorio.keys,
        relatorio.values,
        strict=True,
    ):
        if not isinstance(
            chave,
            ast.Constant,
        ):
            continue

        valores[chave.value] = valor

    assert "commercial_discovery_outcome" in valores

    valor = valores["commercial_discovery_outcome"]

    assert isinstance(
        valor,
        ast.Name,
    )

    assert valor.id == "feedback_discovery_comercial"


def test_feedback_nao_controla_if():
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

        assert "feedback_discovery_comercial" not in nomes
