from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from repositories.fila_publicacao_repository import (
    FilaPublicacaoRepository,
)


def _colunas(
    banco,
    tabela: str,
) -> set[str]:
    with sqlite3.connect(banco) as conexao:
        return {linha[1] for linha in conexao.execute(f'PRAGMA table_info("{tabela}")').fetchall()}


def _oferta_json(
    link: str,
) -> str:
    return json.dumps(
        {
            "nome": "Produto Teste",
            "loja": "Loja Teste",
            "preco": 100.0,
            "preco_antigo": 120.0,
            "link": link,
            "imagem": "https://exemplo/imagem.jpg",
        },
        ensure_ascii=False,
    )


def _inserir_item_raw(
    banco,
    *,
    link: str = "https://exemplo/item",
) -> int:
    agora = datetime.now().astimezone().isoformat(timespec="seconds")

    with sqlite3.connect(banco) as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO fila_publicacao (
                link,
                tipo_oportunidade,
                oferta_json,
                pontuacao,
                prioridade,
                status,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, 'pendente', ?, ?)
            """,
            (
                link,
                "normal",
                _oferta_json(link),
                75.0,
                75.0,
                agora,
                agora,
            ),
        )

        return int(cursor.lastrowid)


def _criar_schema_antigo(
    banco,
) -> None:
    with sqlite3.connect(banco) as conexao:
        conexao.executescript("""
            CREATE TABLE fila_publicacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                link TEXT NOT NULL UNIQUE,
                chave_canonica TEXT,
                chave_familia TEXT,
                familia TEXT,
                confianca_familia REAL NOT NULL DEFAULT 0,
                categoria TEXT,
                marca TEXT,
                tipo_oportunidade TEXT NOT NULL,
                oferta_json TEXT NOT NULL,
                historico_json TEXT,
                pontuacao REAL NOT NULL,
                prioridade REAL NOT NULL,
                deve_republicar_por_queda INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pendente',
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                publicado_em TEXT,
                motivo_saida TEXT,
                segurado_ate TEXT,
                agendado_para TEXT,
                aprovado_manualmente INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE historico_publicacoes_fila (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fila_item_id INTEGER NOT NULL,
                link TEXT NOT NULL,
                chave_canonica TEXT,
                chave_familia TEXT,
                familia TEXT,
                categoria TEXT,
                marca TEXT,
                tipo_oportunidade TEXT NOT NULL,
                oferta_json TEXT NOT NULL,
                pontuacao REAL NOT NULL,
                publicado_em TEXT NOT NULL
            );
            """)


def test_schema_novo_tem_proveniencia_em_fila_e_historico(
    tmp_path,
):
    banco = tmp_path / "fila.sqlite3"

    FilaPublicacaoRepository(str(banco))

    assert "proveniencia_discovery_json" in _colunas(
        banco,
        "fila_publicacao",
    )

    assert "proveniencia_discovery_json" in _colunas(
        banco,
        "historico_publicacoes_fila",
    )


def test_schema_antigo_e_migrado_sem_recriar_banco(
    tmp_path,
):
    banco = tmp_path / "fila_antiga.sqlite3"

    _criar_schema_antigo(banco)

    FilaPublicacaoRepository(str(banco))

    assert "proveniencia_discovery_json" in _colunas(
        banco,
        "fila_publicacao",
    )

    assert "proveniencia_discovery_json" in _colunas(
        banco,
        "historico_publicacoes_fila",
    )


def test_define_proveniencia_por_link(
    tmp_path,
):
    banco = tmp_path / "fila.sqlite3"

    repo = FilaPublicacaoRepository(str(banco))

    link = "https://exemplo/item"

    _inserir_item_raw(
        banco,
        link=link,
    )

    payload = {
        "schema_version": 1,
        "origem": ("commercial_discovery_hunter"),
        "granularidade": ("fonte_hunter"),
        "atribuicao_alvo_individual": False,
        "fontes_hunter_guiadas": ["KabumScraper"],
    }

    repo.definir_proveniencia_discovery_comercial(
        link,
        payload,
    )

    with sqlite3.connect(banco) as conexao:
        valor = conexao.execute(
            """
            SELECT proveniencia_discovery_json
            FROM fila_publicacao
            WHERE link = ?
            """,
            (link,),
        ).fetchone()[0]

    assert json.loads(valor) == payload


def test_none_limpa_proveniencia_antiga(
    tmp_path,
):
    banco = tmp_path / "fila.sqlite3"

    repo = FilaPublicacaoRepository(str(banco))

    link = "https://exemplo/item"

    _inserir_item_raw(
        banco,
        link=link,
    )

    repo.definir_proveniencia_discovery_comercial(
        link,
        {"fontes_hunter_guiadas": ["KabumScraper"]},
    )

    repo.definir_proveniencia_discovery_comercial(
        link,
        None,
    )

    with sqlite3.connect(banco) as conexao:
        valor = conexao.execute(
            """
            SELECT proveniencia_discovery_json
            FROM fila_publicacao
            WHERE link = ?
            """,
            (link,),
        ).fetchone()[0]

    assert valor is None


def test_marcar_publicado_copia_proveniencia_para_historico(
    tmp_path,
):
    banco = tmp_path / "fila.sqlite3"

    repo = FilaPublicacaoRepository(str(banco))

    link = "https://exemplo/item"

    item_id = _inserir_item_raw(
        banco,
        link=link,
    )

    payload = {
        "schema_version": 1,
        "origem": ("commercial_discovery_hunter"),
        "granularidade": ("fonte_hunter"),
        "atribuicao_alvo_individual": False,
        "fontes_hunter_guiadas": [
            "KabumScraper",
            "AliExpressScraper",
        ],
    }

    repo.definir_proveniencia_discovery_comercial(
        link,
        payload,
    )

    repo.marcar_publicado(item_id)

    with sqlite3.connect(banco) as conexao:
        linha = conexao.execute(
            """
            SELECT
                status,
                publicado_em,
                proveniencia_discovery_json
            FROM fila_publicacao
            WHERE id = ?
            """,
            (item_id,),
        ).fetchone()

        historico = conexao.execute(
            """
            SELECT proveniencia_discovery_json
            FROM historico_publicacoes_fila
            WHERE fila_item_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (item_id,),
        ).fetchone()

    assert linha[0] == "publicado"
    assert linha[1]

    assert json.loads(linha[2]) == payload

    assert historico is not None

    assert json.loads(historico[0]) == payload


def test_item_pendente_expoe_proveniencia_convertida(
    tmp_path,
):
    banco = tmp_path / "fila.sqlite3"

    repo = FilaPublicacaoRepository(str(banco))

    link = "https://exemplo/item"

    item_id = _inserir_item_raw(
        banco,
        link=link,
    )

    payload = {
        "schema_version": 1,
        "fontes_hunter_guiadas": ["KabumScraper"],
    }

    repo.definir_proveniencia_discovery_comercial(
        link,
        payload,
    )

    item = repo.obter_pendente_por_id(item_id)

    assert item is not None

    assert item.proveniencia_discovery_comercial == payload
