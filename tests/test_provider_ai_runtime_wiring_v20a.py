from __future__ import annotations

import ast
from pathlib import Path

import pytest

from config.configuracoes import Configuracoes
from services.provedor_http_inteligencia_ai import (
    ProvedorHttpInteligenciaAI,
    criar_provedor_http_inteligencia_ai,
)

VARIAVEIS_PROVIDER = (
    "AI_PROVEDOR_ENDPOINT",
    "AI_PROVEDOR_NOME",
    "AI_PROVEDOR_MODELO",
    "AI_PROVEDOR_AUTH_HEADER_NOME",
    "AI_PROVEDOR_AUTH_HEADER_VALOR",
)


def _ambiente_minimo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "TELEGRAM_BOT_TOKEN",
        "teste",
    )
    monkeypatch.setenv(
        "CHANNEL_ID",
        "-100123",
    )
    monkeypatch.setenv(
        "IDENTIFICADOR_MARCA",
        "teste",
    )

    for nome in VARIAVEIS_PROVIDER:
        monkeypatch.setenv(
            nome,
            "",
        )


def test_config_provider_v20a_e_opcional_por_padrao(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ambiente_minimo(monkeypatch)

    config = Configuracoes()

    assert config.ai_provedor_endpoint is None
    assert config.ai_provedor_nome is None
    assert config.ai_provedor_modelo is None
    assert config.ai_provedor_auth_header_nome is None
    assert config.ai_provedor_auth_header_valor is None


def test_config_exige_nome_quando_endpoint_existe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ambiente_minimo(monkeypatch)
    monkeypatch.setenv(
        "AI_PROVEDOR_ENDPOINT",
        "https://example.invalid/ai",
    )

    with pytest.raises(
        ValueError,
        match="AI_PROVEDOR_NOME",
    ):
        Configuracoes()


def test_config_rejeita_auth_parcial(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _ambiente_minimo(monkeypatch)
    monkeypatch.setenv(
        "AI_PROVEDOR_ENDPOINT",
        "https://example.invalid/ai",
    )
    monkeypatch.setenv(
        "AI_PROVEDOR_NOME",
        "fake",
    )
    monkeypatch.setenv(
        "AI_PROVEDOR_AUTH_HEADER_NOME",
        "Authorization",
    )

    with pytest.raises(
        ValueError,
        match="AI_PROVEDOR_AUTH_HEADER",
    ):
        Configuracoes()


def test_factory_sem_endpoint_retorna_none() -> None:
    assert (
        criar_provedor_http_inteligencia_ai(
            endpoint=None,
            provedor=None,
        )
        is None
    )


def test_factory_cria_adapter_sem_fazer_http() -> None:
    provider = criar_provedor_http_inteligencia_ai(
        endpoint="http://127.0.0.1:9999/ai",
        provedor="fake-local",
        modelo="fake-model",
        auth_header_nome="Authorization",
        auth_header_valor="Bearer segredo-teste",
    )

    assert isinstance(
        provider,
        ProvedorHttpInteligenciaAI,
    )
    assert provider.endpoint == ("http://127.0.0.1:9999/ai")
    assert provider.provedor == "fake-local"
    assert provider.modelo == "fake-model"
    assert provider.cabecalhos == {
        "Authorization": "Bearer segredo-teste",
    }


def test_factory_rejeita_configuracao_parcial() -> None:
    with pytest.raises(ValueError):
        criar_provedor_http_inteligencia_ai(
            endpoint=None,
            provedor="fake",
        )

    with pytest.raises(ValueError):
        criar_provedor_http_inteligencia_ai(
            endpoint="https://example.invalid/ai",
            provedor=None,
        )

    with pytest.raises(ValueError):
        criar_provedor_http_inteligencia_ai(
            endpoint="https://example.invalid/ai",
            provedor="fake",
            auth_header_nome="Authorization",
            auth_header_valor=None,
        )


def test_main_repassa_mesmo_provider_aos_dois_consumidores() -> None:
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    arvore = ast.parse(texto)

    chamadas = [node for node in ast.walk(arvore) if isinstance(node, ast.Call)]

    provider_factory = [
        node
        for node in chamadas
        if isinstance(
            node.func,
            ast.Name,
        )
        and node.func.id == "criar_provedor_http_inteligencia_ai"
    ]

    assert len(provider_factory) == 1

    consumidor_nomes = {
        "ClassificadorProdutoAssistidoAI",
        "CuradoriaPublicacaoAssistidaAI",
    }

    consumidores = {}

    for node in chamadas:
        if not isinstance(
            node.func,
            ast.Name,
        ):
            continue

        if node.func.id not in consumidor_nomes:
            continue

        consumidores[node.func.id] = {kw.arg: kw.value for kw in node.keywords}

    assert set(consumidores) == consumidor_nomes

    for kwargs in consumidores.values():
        habilitado = kwargs["habilitado"]

        assert isinstance(
            habilitado,
            ast.Constant,
        )
        assert habilitado.value is False

        provedor = kwargs["provedor"]

        assert isinstance(
            provedor,
            ast.Name,
        )
        assert provedor.id == "provedor_ai"


def test_main_factory_usa_somente_configuracao_generica() -> None:
    texto = Path("main.py").read_text(encoding="utf-8-sig")

    assert "criar_provedor_http_inteligencia_ai" in texto

    for atributo in (
        "ai_provedor_endpoint",
        "ai_provedor_nome",
        "ai_provedor_modelo",
        "ai_provedor_auth_header_nome",
        "ai_provedor_auth_header_valor",
    ):
        assert f"configuracoes.{atributo}" in texto

    for proibido in (
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "api.openai.com",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
    ):
        assert proibido not in texto


def test_env_example_documenta_provider_sem_segredo_real() -> None:
    texto = Path(".env.example").read_text(encoding="utf-8-sig")

    for nome in VARIAVEIS_PROVIDER:
        assert f"{nome}=" in texto

    assert "Bearer segredo-teste" not in texto
    assert "sk-" not in texto
