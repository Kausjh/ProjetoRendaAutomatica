from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta

from repositories.fila_publicacao_repository import (
    FilaPublicacaoRepository,
)


def _inserir_publicacao(
    banco,
    *,
    link: str,
    proveniencia,
    publicado_em: str,
) -> None:
    with sqlite3.connect(banco) as conexao:
        conexao.execute(
            """
            INSERT INTO historico_publicacoes_fila (
                fila_item_id,
                link,
                tipo_oportunidade,
                oferta_json,
                pontuacao,
                publicado_em,
                proveniencia_discovery_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                link,
                "normal",
                "{}",
                75.0,
                publicado_em,
                (
                    json.dumps(
                        proveniencia,
                        ensure_ascii=False,
                    )
                    if proveniencia is not None
                    else None
                ),
            ),
        )


def test_historico_discovery_converte_proveniencia(
    tmp_path,
):
    banco = tmp_path / "fila.sqlite3"

    repo = FilaPublicacaoRepository(str(banco))

    payload = {
        "schema_version": 1,
        "origem": ("commercial_discovery_hunter"),
        "granularidade": ("fonte_hunter"),
        "fontes_hunter_guiadas": ["KabumScraper"],
    }

    _inserir_publicacao(
        banco,
        link="https://exemplo/1",
        proveniencia=payload,
        publicado_em=(datetime.now().astimezone().isoformat(timespec="seconds")),
    )

    historico = repo.historico_publicacoes_discovery_comercial()

    assert len(historico) == 1

    assert historico[0]["proveniencia_discovery_comercial"] == payload

    assert "proveniencia_discovery_json" not in historico[0]


def test_historico_discovery_preserva_publicacao_sem_proveniencia(
    tmp_path,
):
    banco = tmp_path / "fila.sqlite3"

    repo = FilaPublicacaoRepository(str(banco))

    _inserir_publicacao(
        banco,
        link="https://exemplo/1",
        proveniencia=None,
        publicado_em=(datetime.now().astimezone().isoformat(timespec="seconds")),
    )

    historico = repo.historico_publicacoes_discovery_comercial()

    assert len(historico) == 1

    assert historico[0]["proveniencia_discovery_comercial"] is None


def test_historico_discovery_json_invalido_nao_quebra(
    tmp_path,
):
    banco = tmp_path / "fila.sqlite3"

    repo = FilaPublicacaoRepository(str(banco))

    agora = datetime.now().astimezone().isoformat(timespec="seconds")

    with sqlite3.connect(banco) as conexao:
        conexao.execute(
            """
            INSERT INTO historico_publicacoes_fila (
                fila_item_id,
                link,
                tipo_oportunidade,
                oferta_json,
                pontuacao,
                publicado_em,
                proveniencia_discovery_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                1,
                "https://exemplo/1",
                "normal",
                "{}",
                75.0,
                agora,
                "{json-invalido",
            ),
        )

    historico = repo.historico_publicacoes_discovery_comercial()

    assert historico[0]["proveniencia_discovery_comercial"] is None


def test_historico_discovery_respeita_limite_e_ordem(
    tmp_path,
):
    banco = tmp_path / "fila.sqlite3"

    repo = FilaPublicacaoRepository(str(banco))

    agora = datetime.now().astimezone()

    for indice in range(3):
        _inserir_publicacao(
            banco,
            link=("https://exemplo/" f"{indice}"),
            proveniencia=None,
            publicado_em=(agora + timedelta(seconds=indice)).isoformat(timespec="seconds"),
        )

    historico = repo.historico_publicacoes_discovery_comercial(limite=2)

    assert len(historico) == 2

    assert historico[0]["link"] == "https://exemplo/2"

    assert historico[1]["link"] == "https://exemplo/1"


def test_historico_discovery_limite_zero_ainda_e_seguro(
    tmp_path,
):
    banco = tmp_path / "fila.sqlite3"

    repo = FilaPublicacaoRepository(str(banco))

    _inserir_publicacao(
        banco,
        link="https://exemplo/1",
        proveniencia=None,
        publicado_em=(datetime.now().astimezone().isoformat(timespec="seconds")),
    )

    historico = repo.historico_publicacoes_discovery_comercial(limite=0)

    assert len(historico) == 1
