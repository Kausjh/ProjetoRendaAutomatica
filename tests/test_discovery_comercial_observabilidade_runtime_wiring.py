import ast
from pathlib import Path

MAIN = Path("main.py")
EXECUTOR = Path("services/executor_pipeline.py")


def _nome_chamada(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return None


def test_main_cria_observabilidade_depois_dos_scrapers_e_entrega_ao_pipeline():
    arvore = ast.parse(MAIN.read_text(encoding="utf-8-sig"))

    funcao_main = next(
        node
        for node in arvore.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "main"
    )

    linha_scrapers = None
    linha_observabilidade = None
    linha_pipeline = None
    pipeline_recebe_observabilidade = False

    for node in ast.walk(funcao_main):
        if not isinstance(node, ast.Assign):
            continue

        if len(node.targets) != 1:
            continue

        alvo = node.targets[0]

        if not isinstance(alvo, ast.Name):
            continue

        if (
            alvo.id == "scrapers"
            and isinstance(node.value, ast.Call)
            and _nome_chamada(node.value.func) == "criar_scrapers"
        ):
            linha_scrapers = node.lineno

        if (
            alvo.id == "observabilidade_discovery_comercial_hunter"
            and isinstance(node.value, ast.Call)
            and _nome_chamada(node.value.func) == "criar_observabilidade_discovery_comercial_hunter"
        ):
            linha_observabilidade = node.lineno

        if (
            alvo.id == "pipeline"
            and isinstance(node.value, ast.Call)
            and _nome_chamada(node.value.func) == "ExecutorPipeline"
        ):
            linha_pipeline = node.lineno

            pipeline_recebe_observabilidade = any(
                keyword.arg == "observabilidade_discovery_comercial_hunter"
                for keyword in node.value.keywords
            )

    assert linha_scrapers is not None
    assert linha_observabilidade is not None
    assert linha_pipeline is not None
    assert linha_scrapers < linha_observabilidade < linha_pipeline
    assert pipeline_recebe_observabilidade is True


def test_executor_persiste_observabilidade_no_relatorio_do_ciclo():
    texto = EXECUTOR.read_text(encoding="utf-8-sig")
    arvore = ast.parse(texto)

    classe = next(
        node
        for node in arvore.body
        if isinstance(node, ast.ClassDef) and node.name == "ExecutorPipeline"
    )

    construtor = next(
        node
        for node in classe.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )

    parametros = {argumento.arg for argumento in construtor.args.args}

    assert "observabilidade_discovery_comercial_hunter" in parametros

    funcao_executar = next(
        node
        for node in classe.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "executar"
    )

    atribuicao_relatorio = next(
        node
        for node in ast.walk(funcao_executar)
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "relatorio"
        and isinstance(node.value, ast.Dict)
    )

    valor_observabilidade = None

    for chave, valor in zip(
        atribuicao_relatorio.value.keys,
        atribuicao_relatorio.value.values,
        strict=True,
    ):
        if not (isinstance(chave, ast.Constant) and chave.value == "discovery_comercial_hunter"):
            continue

        valor_observabilidade = valor
        break

    assert isinstance(
        valor_observabilidade,
        ast.Attribute,
    )
    assert valor_observabilidade.attr == ("observabilidade_discovery_comercial_hunter")
    assert isinstance(
        valor_observabilidade.value,
        ast.Name,
    )
    assert valor_observabilidade.value.id == "self"
