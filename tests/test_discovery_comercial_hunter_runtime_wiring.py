import ast
from pathlib import Path

MAIN = Path("main.py")


def _nome_chamada(
    node,
):
    if isinstance(
        node,
        ast.Name,
    ):
        return node.id

    if isinstance(
        node,
        ast.Attribute,
    ):
        return node.attr

    return None


def test_main_aplica_discovery_comercial_entre_budget_base_e_coletor():
    texto = MAIN.read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    assert (
        "from services.scout."
        "wiring_discovery_comercial_hunter "
        "import aplicar_discovery_comercial_hunter" in texto
    )

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

    linha_budget_base = None
    linha_aplicar = None
    linha_mapping = None
    linha_coletor = None

    coletor_usa_mapping = False

    for node in ast.walk(main):

        if isinstance(
            node,
            ast.Assign,
        ):

            if len(node.targets) != 1:
                continue

            alvo = node.targets[0]

            if not isinstance(
                alvo,
                ast.Name,
            ):
                continue

            if (
                alvo.id == "limites_hunter_por_fonte"
                and isinstance(
                    node.value,
                    ast.Call,
                )
                and _nome_chamada(node.value.func) == "carregar_limites_hunter_por_fonte"
            ):
                linha_budget_base = node.lineno

            if (
                alvo.id == "resultado_discovery_comercial"
                and isinstance(
                    node.value,
                    ast.Call,
                )
                and _nome_chamada(node.value.func) == "aplicar_discovery_comercial_hunter"
            ):
                linha_aplicar = node.lineno

            if (
                alvo.id == "limites_hunter_por_fonte"
                and isinstance(
                    node.value,
                    ast.Call,
                )
                and _nome_chamada(node.value.func) == "como_mapping"
            ):
                linha_mapping = node.lineno

        if not isinstance(
            node,
            ast.Call,
        ):
            continue

        if _nome_chamada(node.func) != "ColetorOfertas":
            continue

        linha_coletor = node.lineno

        for keyword in node.keywords:

            if keyword.arg != "limites_hunter_por_fonte":
                continue

            coletor_usa_mapping = (
                isinstance(
                    keyword.value,
                    ast.Name,
                )
                and keyword.value.id == "limites_hunter_por_fonte"
            )

    assert linha_budget_base is not None

    assert linha_aplicar is not None
    assert linha_mapping is not None
    assert linha_coletor is not None

    assert linha_budget_base < linha_aplicar < linha_mapping < linha_coletor

    assert coletor_usa_mapping is True
