from __future__ import annotations

import ast
import json
import urllib.request
from pathlib import Path

from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from services.controle.controlador import ControladorAdministrativo
from services.controle.servidor_status import ServidorStatusAdministrativo


def _snapshot_exemplo() -> dict[str, object]:
    return {
        "kill_switch_ativo": True,
        "limite_chamadas_externas": 25,
        "limite_tokens_total": 50000,
        "limite_custo_estimado_usd": 0.5,
        "chamadas_reservadas": 0,
        "bloqueio_limite_ativo": False,
        "motivo_bloqueio_limite": None,
        "observabilidade": {
            "eventos_total": 0,
            "chamadas_externas_total": 0,
            "tokens_total": 0,
            "custo_estimado_usd_total": 0.0,
        },
        "circuit_breaker": {
            "estado": "CLOSED",
            "falhas_consecutivas": 0,
        },
    }


def test_repository_persiste_e_recupera_snapshot_ai(tmp_path: Path) -> None:
    caminho = tmp_path / "controle.sqlite3"
    repo = ControleAdministrativoRepository(caminho_arquivo=str(caminho))
    snapshot = _snapshot_exemplo()

    repo.salvar_snapshot_operacional_ai(snapshot)

    outro_processo = ControleAdministrativoRepository(caminho_arquivo=str(caminho))
    dados = outro_processo.obter_snapshot_operacional_ai()

    assert dados is not None
    assert dados["schema_version"] == 1
    assert isinstance(dados["capturado_em"], str)
    assert dados["capturado_em"]
    assert dados["snapshot"] == snapshot


def test_repository_snapshot_ai_ausente_retorna_none(tmp_path: Path) -> None:
    repo = ControleAdministrativoRepository(caminho_arquivo=str(tmp_path / "controle.sqlite3"))
    assert repo.obter_snapshot_operacional_ai() is None


def test_repository_snapshot_ai_corrompido_falha_fechado(tmp_path: Path) -> None:
    repo = ControleAdministrativoRepository(caminho_arquivo=str(tmp_path / "controle.sqlite3"))
    repo.definir_estado(
        chave="snapshot_operacional_ai_v1",
        valor="{nao-json",
    )
    assert repo.obter_snapshot_operacional_ai() is None


def test_controlador_expoe_snapshot_read_only(tmp_path: Path) -> None:
    repo = ControleAdministrativoRepository(caminho_arquivo=str(tmp_path / "controle.sqlite3"))
    snapshot = _snapshot_exemplo()
    repo.salvar_snapshot_operacional_ai(snapshot)

    controlador = object.__new__(ControladorAdministrativo)
    controlador.repositorio_admin = repo

    dados = controlador.obter_snapshot_operacional_ai()

    assert dados["disponivel"] is True
    assert dados["schema_version"] == 1
    assert dados["snapshot"] == snapshot


def test_controlador_snapshot_ausente_tem_resposta_estavel(tmp_path: Path) -> None:
    repo = ControleAdministrativoRepository(caminho_arquivo=str(tmp_path / "controle.sqlite3"))
    controlador = object.__new__(ControladorAdministrativo)
    controlador.repositorio_admin = repo

    assert controlador.obter_snapshot_operacional_ai() == {
        "disponivel": False,
        "schema_version": 1,
        "capturado_em": None,
        "snapshot": None,
    }


def test_rota_get_ia_operacional_responde_snapshot() -> None:
    class ControladorFake:
        def obter_snapshot_operacional_ai(self) -> dict[str, object]:
            return {
                "disponivel": True,
                "schema_version": 1,
                "capturado_em": "2026-09-12T12:00:00-03:00",
                "snapshot": _snapshot_exemplo(),
            }

    servidor = ServidorStatusAdministrativo(
        controlador=ControladorFake(),
        host="127.0.0.1",
        porta=0,
        token="",
    )
    servidor.iniciar()

    try:
        assert servidor._servidor is not None
        porta = int(servidor._servidor.server_address[1])

        with urllib.request.urlopen(
            f"http://127.0.0.1:{porta}/ia/operacional",
            timeout=3,
        ) as resposta:
            status = resposta.status
            dados = json.loads(resposta.read().decode("utf-8"))

        assert status == 200
        assert dados["disponivel"] is True
        assert dados["snapshot"]["kill_switch_ativo"] is True
    finally:
        servidor.encerrar()


def test_main_persiste_snapshot_ai_em_finally() -> None:
    texto = Path("main.py").read_text(encoding="utf-8-sig")
    arvore = ast.parse(texto)

    main = next(
        node
        for node in arvore.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "main"
    )

    encontrou = False

    for node in ast.walk(main):
        if not isinstance(node, ast.Try):
            continue

        corpo = ast.unparse(ast.Module(body=node.body, type_ignores=[]))
        final = ast.unparse(ast.Module(body=node.finalbody, type_ignores=[]))

        if (
            "await pipeline.executar()" in corpo
            and "salvar_snapshot_operacional_ai" in final
            and "controle_operacional_ai.snapshot()" in final
            and "asdict" in final
        ):
            encontrou = True
            break

    assert encontrou is True


def test_main_persistencia_snapshot_ai_nao_ativa_provider() -> None:
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    assert texto.count("habilitado=False") >= 2

    for item in (
        "ProvedorHttpInteligenciaAI(",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
    ):
        assert item not in texto


# 63.8738, -149.7525
