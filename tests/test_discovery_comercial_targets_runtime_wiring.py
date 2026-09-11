import ast
from pathlib import Path

MAIN = Path("main.py")


def _nome_chamada(node):
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return node.attr

    return None


def test_main_carrega_alvos_antes_de_criar_scrapers():
    texto = MAIN.read_text(encoding="utf-8-sig")
    arvore = ast.parse(texto)

    assert "from services.scout." "wiring_alvos_discovery_comercial_hunter import (" in texto

    main = next(
        node
        for node in arvore.body
        if (isinstance(node, ast.AsyncFunctionDef) and node.name == "main")
    )

    linha_alvos = None
    linha_scrapers = None
    scrapers_recebem_alvos = False

    for node in ast.walk(main):
        if not isinstance(node, ast.Assign):
            continue

        if len(node.targets) != 1:
            continue

        alvo = node.targets[0]

        if (
            isinstance(alvo, ast.Name)
            and alvo.id == "resultado_alvos_discovery_comercial"
            and isinstance(node.value, ast.Call)
            and _nome_chamada(node.value.func) == "carregar_alvos_discovery_comercial_hunter"
        ):
            linha_alvos = node.lineno

        if (
            isinstance(alvo, ast.Name)
            and alvo.id == "scrapers"
            and isinstance(node.value, ast.Call)
            and _nome_chamada(node.value.func) == "criar_scrapers"
        ):
            linha_scrapers = node.lineno

            for keyword in node.value.keywords:
                if keyword.arg == "alvos_discovery_comercial":
                    scrapers_recebem_alvos = True

    assert linha_alvos is not None
    assert linha_scrapers is not None
    assert linha_alvos < linha_scrapers
    assert scrapers_recebem_alvos is True
