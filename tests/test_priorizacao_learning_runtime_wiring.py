import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MAIN = ROOT / "main.py"


def _main():
    texto = MAIN.read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    funcao = next(
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.AsyncFunctionDef,
        )
        and node.name == "main"
    )

    return (
        texto,
        arvore,
        funcao,
    )


def _calls(
    funcao,
    nome,
):
    return [
        node
        for node in ast.walk(funcao)
        if isinstance(
            node,
            ast.Call,
        )
        and isinstance(
            node.func,
            ast.Name,
        )
        and node.func.id == nome
    ]


def test_importa_wiring_priorizacao_learning():
    _, arvore, _ = _main()

    imports = [
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.ImportFrom,
        )
        and node.module
        == ("services.scout." "wiring_priorizacao_learning_" "discovery_comercial_hunter")
    ]

    assert len(imports) == 1


def test_reutiliza_relatorios_repository():
    texto, _, _ = _main()

    assert texto.count("RelatoriosRepository()") == 1

    assert "relatorios_repository.listar()" in texto

    assert "database/relatorios_execucao.json" not in texto


def test_priorizacao_ocorre_antes_de_criar_scrapers():
    _, _, funcao = _main()

    priorizacoes = _calls(
        funcao,
        "aplicar_priorizacao_learning_com_historico",
    )

    scrapers = _calls(
        funcao,
        "criar_scrapers",
    )

    assert len(priorizacoes) == 1

    assert len(scrapers) == 1

    assert priorizacoes[0].lineno < scrapers[0].lineno


def test_resultado_priorizado_substitui_resultado_dos_alvos():
    _, _, funcao = _main()

    atribuicoes = [
        node
        for node in ast.walk(funcao)
        if isinstance(
            node,
            ast.Assign,
        )
        and any(
            isinstance(
                alvo,
                ast.Name,
            )
            and alvo.id == "resultado_alvos_discovery_comercial"
            for alvo in node.targets
        )
        and isinstance(
            node.value,
            ast.Attribute,
        )
        and node.value.attr == "resultado"
        and isinstance(
            node.value.value,
            ast.Name,
        )
        and node.value.value.id == "resultado_priorizacao_learning"
    ]

    assert len(atribuicoes) == 1


def test_criar_scrapers_consome_resultado_ja_priorizado():
    _, _, funcao = _main()

    chamadas = _calls(
        funcao,
        "criar_scrapers",
    )

    assert len(chamadas) == 1

    chamada = chamadas[0]

    argumento = next(item for item in chamada.keywords if item.arg == "alvos_discovery_comercial")

    atributos = [
        node
        for node in ast.walk(argumento.value)
        if isinstance(
            node,
            ast.Attribute,
        )
        and node.attr == "alvos"
        and isinstance(
            node.value,
            ast.Name,
        )
        and node.value.id == "resultado_alvos_discovery_comercial"
    ]

    assert len(atributos) == 1


def test_fail_open_na_leitura_dos_relatorios():
    texto, _, _ = _main()

    assert "except Exception as erro:" in texto

    assert "relatorios_learning_existentes = []" in texto


def test_observabilidade_da_priorizacao_e_persistida():
    texto, _, _ = _main()

    assert '"priorizacao_learning"' in texto

    assert "resultado_priorizacao_learning.observabilidade" in texto


def test_executor_pipeline_nao_precisou_ser_alterado():
    arquivo = ROOT / "services" / "executor_pipeline.py"

    texto = arquivo.read_text(encoding="utf-8-sig")

    assert "priorizacao_learning" not in texto


def test_wiring_nao_altera_score_de_oferta():
    texto, _, _ = _main()

    assert "aplicar_priorizacao_learning_com_historico" in texto

    assert "PontuadorOferta" in texto
