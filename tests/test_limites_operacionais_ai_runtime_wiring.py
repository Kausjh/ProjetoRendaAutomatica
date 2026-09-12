from __future__ import annotations

import ast
from pathlib import Path

DEFAULT_CHAMADAS = 25
DEFAULT_TOKENS_TOTAL = 50_000
DEFAULT_CUSTO_USD = 0.50


def _classe(
    arvore: ast.Module,
    nome: str,
) -> ast.ClassDef:
    encontrados = [
        node for node in arvore.body if isinstance(node, ast.ClassDef) and node.name == nome
    ]

    assert len(encontrados) == 1
    return encontrados[0]


def _metodo(
    classe: ast.ClassDef,
    nome: str,
) -> ast.FunctionDef:
    encontrados = [
        node for node in classe.body if isinstance(node, ast.FunctionDef) and node.name == nome
    ]

    assert len(encontrados) == 1
    return encontrados[0]


def _atributos_self(
    funcao: ast.FunctionDef,
) -> dict[str, ast.AST]:
    saida = {}

    for stmt in funcao.body:
        if not isinstance(stmt, ast.Assign):
            continue

        if len(stmt.targets) != 1:
            continue

        target = stmt.targets[0]

        if not (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            continue

        saida[target.attr] = stmt.value

    return saida


def test_config_define_limites_ai_com_defaults_conservadores():
    texto = Path("config/configuracoes.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)
    classe = _classe(
        arvore,
        "Configuracoes",
    )
    init = _metodo(
        classe,
        "__init__",
    )
    attrs = _atributos_self(init)

    casos = {
        "ai_limite_chamadas_externas": (
            "_buscar_inteiro",
            "AI_LIMITE_CHAMADAS_EXTERNAS",
            DEFAULT_CHAMADAS,
        ),
        "ai_limite_tokens_total": (
            "_buscar_inteiro",
            "AI_LIMITE_TOKENS_TOTAL",
            DEFAULT_TOKENS_TOTAL,
        ),
        "ai_limite_custo_estimado_usd": (
            "_buscar_decimal",
            "AI_LIMITE_CUSTO_ESTIMADO_USD",
            DEFAULT_CUSTO_USD,
        ),
    }

    for atributo, (
        metodo,
        nome_env,
        valor_padrao,
    ) in casos.items():
        call = attrs[atributo]

        assert isinstance(
            call,
            ast.Call,
        )

        assert isinstance(
            call.func,
            ast.Attribute,
        )

        assert call.func.attr == metodo

        kwargs = {kw.arg: kw.value for kw in call.keywords}

        assert kwargs["nome"].value == nome_env

        assert kwargs["valor_padrao"].value == valor_padrao


def test_config_valida_limites_ai_como_positivos():
    texto = Path("config/configuracoes.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)
    classe = _classe(
        arvore,
        "Configuracoes",
    )
    validar = _metodo(
        classe,
        "_validar",
    )

    atributos_comparados = set()

    for node in ast.walk(validar):
        if not isinstance(
            node,
            ast.Compare,
        ):
            continue

        esquerda = node.left

        if (
            isinstance(
                esquerda,
                ast.Attribute,
            )
            and isinstance(
                esquerda.value,
                ast.Name,
            )
            and esquerda.value.id == "self"
        ):
            atributos_comparados.add(esquerda.attr)

    assert {
        "ai_limite_chamadas_externas",
        "ai_limite_tokens_total",
        "ai_limite_custo_estimado_usd",
    }.issubset(atributos_comparados)


def test_main_repassa_todos_os_limites_para_controle_compartilhado():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    main = next(
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.AsyncFunctionDef,
        )
        and node.name == "main"
    )

    assignments = {
        node.targets[0].id: node.value
        for node in main.body
        if isinstance(
            node,
            ast.Assign,
        )
        and len(node.targets) == 1
        and isinstance(
            node.targets[0],
            ast.Name,
        )
    }

    controle = assignments["controle_operacional_ai"]

    assert isinstance(
        controle,
        ast.Call,
    )

    kwargs = {keyword.arg: keyword.value for keyword in controle.keywords}

    esperado = {
        "kill_switch_ativo": "ai_kill_switch_ativo",
        "limite_chamadas_externas": ("ai_limite_chamadas_externas"),
        "limite_tokens_total": ("ai_limite_tokens_total"),
        "limite_custo_estimado_usd": ("ai_limite_custo_estimado_usd"),
    }

    assert set(kwargs) == set(esperado)

    for nome_kw, atributo_config in esperado.items():
        valor = kwargs[nome_kw]

        assert isinstance(
            valor,
            ast.Attribute,
        )

        assert valor.attr == atributo_config

        assert isinstance(
            valor.value,
            ast.Name,
        )

        assert valor.value.id == "configuracoes"


def test_consumidores_continuam_desligados_e_compartilham_controle():
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    main = next(
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.AsyncFunctionDef,
        )
        and node.name == "main"
    )

    assignments = {
        node.targets[0].id: node.value
        for node in main.body
        if isinstance(
            node,
            ast.Assign,
        )
        and len(node.targets) == 1
        and isinstance(
            node.targets[0],
            ast.Name,
        )
    }

    for nome in (
        "classificador",
        "curadoria_publicacao",
    ):
        call = assignments[nome]
        kwargs = {kw.arg: kw.value for kw in call.keywords}

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


def test_main_continua_sem_provider_endpoint_ou_api_key_ai():
    texto = Path("main.py").read_text(encoding="utf-8-sig").lower()

    proibidos = (
        "openai_api_key",
        "anthropic_api_key",
        "gemini_api_key",
        "provedorhttpinteligenciaai(",
        "api.openai.com",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
    )

    for item in proibidos:
        assert item not in texto


# 63.8738, -149.7525
