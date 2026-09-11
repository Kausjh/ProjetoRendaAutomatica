import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXECUTOR = ROOT / "services" / "executor_pipeline.py"


def _executor():
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


def test_importa_janela_learning():
    _, arvore, _ = _executor()

    imports = [
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.ImportFrom,
        )
        and node.module == ("services.scout." "janela_learning_" "discovery_comercial_hunter")
    ]

    assert len(imports) == 1


def test_importa_score_learning():
    _, arvore, _ = _executor()

    imports = [
        node
        for node in arvore.body
        if isinstance(
            node,
            ast.ImportFrom,
        )
        and node.module == ("services.scout." "score_learning_" "discovery_comercial_hunter")
    ]

    assert len(imports) == 1


def test_runtime_reutiliza_relatorios_repository():
    texto, _, _ = _executor()

    assert "self.relatorios_repository" in texto

    assert '"listar"' in texto

    assert "database/relatorios_execucao.json" not in texto


def test_runtime_inclui_ciclo_atual():
    texto, _, _ = _executor()

    assert "relatorios_learning.append(" in texto

    assert '"data_hora": data_hora_ciclo' in texto

    assert '"commercial_discovery_outcome": (' in texto


def test_runtime_usa_reader_learning_publicacoes():
    texto, _, _ = _executor()

    assert '"historico_publicacoes_"' in texto

    assert '"discovery_comercial_learning"' in texto


def test_janela_e_score_chamados_uma_vez():
    _, _, executar = _executor()

    janela = [
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
        and node.func.id == ("criar_janela_learning_" "discovery_comercial_hunter")
    ]

    score = [
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
        and node.func.id == ("criar_score_learning_" "discovery_comercial_hunter")
    ]

    assert len(janela) == 1

    assert len(score) == 1


def test_relatorio_persiste_learning():
    _, _, executar = _executor()

    encontrou = False

    for node in ast.walk(executar):

        if not isinstance(
            node,
            ast.Dict,
        ):
            continue

        chaves = {
            chave.value
            for chave in node.keys
            if isinstance(
                chave,
                ast.Constant,
            )
            and isinstance(
                chave.value,
                str,
            )
        }

        if "commercial_discovery_learning" in chaves:
            encontrou = True

    assert encontrou is True


def test_learning_e_observacional():
    texto, _, _ = _executor()

    assert '"modo": "observacional"' in texto

    assert '"influencia_priorizacao": False' in texto


def test_learning_nao_controla_decisoes():
    _, _, executar = _executor()

    proibidos = {
        "learning_discovery_comercial",
        "janela_learning_discovery",
        "score_learning_discovery",
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

        assert not (nomes & proibidos)


def test_publicacao_continua_fora_score():
    arquivo = ROOT / "services" / "scout" / ("score_learning_" "discovery_comercial_hunter.py")

    texto = arquivo.read_text(encoding="utf-8-sig")

    assert '"publicacao_entra_no_score": False' in texto
