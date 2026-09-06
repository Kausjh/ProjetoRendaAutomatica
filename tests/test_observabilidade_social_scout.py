# 63.8738, -149.7525

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from services.scout.observabilidade_social_scout import (
    coletar_metricas,
    formatar_relatorio,
)


def criar_banco(
    caminho: Path,
) -> None:
    with sqlite3.connect(caminho) as conexao:
        conexao.executescript("""
            CREATE TABLE mensagens_social_scout (
                fonte TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                PRIMARY KEY (
                    fonte,
                    chat_id,
                    message_id
                )
            );

            CREATE TABLE processamentos_social_scout (
                fonte TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                versao_processador TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                status TEXT NOT NULL,
                motivo TEXT NOT NULL,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL,
                PRIMARY KEY (
                    fonte,
                    chat_id,
                    message_id,
                    versao_processador
                )
            );
            """)


def inserir_mensagem(
    caminho: Path,
    *,
    message_id: int,
    atualizado_em: str,
    chat_id: str = "chat-secreto",
    payload: str = '{"texto":"SEGREDO"}',
) -> None:
    with sqlite3.connect(caminho) as conexao:
        conexao.execute(
            """
            INSERT INTO mensagens_social_scout (
                fonte,
                chat_id,
                message_id,
                payload_json,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "telegram",
                chat_id,
                message_id,
                payload,
                "2026-09-06 18:00:00",
                atualizado_em,
            ),
        )


def inserir_processamento(
    caminho: Path,
    *,
    message_id: int,
    versao: str,
    status: str,
    atualizado_em: str,
    chat_id: str = "chat-secreto",
) -> None:
    with sqlite3.connect(caminho) as conexao:
        conexao.execute(
            """
            INSERT INTO processamentos_social_scout (
                fonte,
                chat_id,
                message_id,
                versao_processador,
                fingerprint,
                status,
                motivo,
                criado_em,
                atualizado_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "telegram",
                chat_id,
                message_id,
                versao,
                f"fingerprint-{message_id}",
                status,
                "motivo interno",
                "2026-09-06 18:01:00",
                atualizado_em,
            ),
        )


def test_coleta_metricas_agregadas(
    tmp_path: Path,
) -> None:
    banco = tmp_path / "social.sqlite3"

    criar_banco(banco)

    for message_id in (
        1,
        2,
        3,
    ):
        inserir_mensagem(
            banco,
            message_id=message_id,
            atualizado_em=("2026-09-06 18:00:00"),
        )

    inserir_processamento(
        banco,
        message_id=1,
        versao="1",
        status="ignorada",
        atualizado_em=("2026-09-06 18:02:00"),
    )

    inserir_processamento(
        banco,
        message_id=2,
        versao="1",
        status="sombra_fora_nicho",
        atualizado_em=("2026-09-06 18:02:00"),
    )

    metricas = coletar_metricas(
        banco,
        versao_processador="1",
    )

    assert metricas.mensagens_raw == 3
    assert metricas.processamentos_total == 2
    assert metricas.processamentos_versao == 2
    assert metricas.sem_estado_versao == 1
    assert metricas.pendencias_observaveis == 1
    assert metricas.cobertura_percentual == 66.67

    assert metricas.status == {
        "ignorada": 1,
        "sombra_fora_nicho": 1,
    }

    assert metricas.candidatas_sombra == 1
    assert metricas.sombra_nicho == 0
    assert metricas.sombra_fora_nicho == 1
    assert metricas.taxa_nicho_sombra_percentual == 0.0


def test_isola_versao_do_processador(
    tmp_path: Path,
) -> None:
    banco = tmp_path / "social.sqlite3"

    criar_banco(banco)

    inserir_mensagem(
        banco,
        message_id=1,
        atualizado_em=("2026-09-06 18:00:00"),
    )

    inserir_processamento(
        banco,
        message_id=1,
        versao="1",
        status="ignorada",
        atualizado_em=("2026-09-06 18:02:00"),
    )

    metricas_v2 = coletar_metricas(
        banco,
        versao_processador="2",
    )

    assert metricas_v2.processamentos_total == 1
    assert metricas_v2.processamentos_versao == 0
    assert metricas_v2.sem_estado_versao == 1
    assert metricas_v2.pendencias_observaveis == 1
    assert metricas_v2.status == {}


def test_detecta_raw_atualizada_depois_do_estado(
    tmp_path: Path,
) -> None:
    banco = tmp_path / "social.sqlite3"

    criar_banco(banco)

    inserir_mensagem(
        banco,
        message_id=1,
        atualizado_em=("2026-09-06 18:10:00"),
    )

    inserir_processamento(
        banco,
        message_id=1,
        versao="1",
        status="ignorada",
        atualizado_em=("2026-09-06 18:05:00"),
    )

    metricas = coletar_metricas(
        banco,
        versao_processador="1",
    )

    assert metricas.sem_estado_versao == 0

    assert metricas.raw_atualizadas_depois_estado == 1

    assert metricas.pendencias_observaveis == 1


def test_relatorio_nao_expoe_payload_ou_ids(
    tmp_path: Path,
) -> None:
    banco = tmp_path / "social.sqlite3"

    criar_banco(banco)

    inserir_mensagem(
        banco,
        message_id=999999,
        atualizado_em=("2026-09-06 18:00:00"),
        chat_id=("CHAT_ID_ULTRA_SECRETO"),
        payload=('{"texto":"MENSAGEM_ULTRA_SECRETA"}'),
    )

    metricas = coletar_metricas(
        banco,
        versao_processador="1",
    )

    relatorio = formatar_relatorio(metricas)

    assert "CHAT_ID_ULTRA_SECRETO" not in relatorio

    assert "MENSAGEM_ULTRA_SECRETA" not in relatorio

    assert "999999" not in relatorio


def test_cli_funciona_executado_como_script(
    tmp_path: Path,
) -> None:
    banco = tmp_path / "social.sqlite3"

    criar_banco(banco)

    inserir_mensagem(
        banco,
        message_id=1,
        atualizado_em=("2026-09-06 18:00:00"),
    )

    raiz_projeto = Path(__file__).resolve().parents[1]

    script = raiz_projeto / "scripts" / "diagnostico_social_scout.py"

    resultado = subprocess.run(
        [
            sys.executable,
            str(script),
            "--database",
            str(banco),
            "--versao",
            "1",
            "--json",
        ],
        cwd=raiz_projeto,
        capture_output=True,
        text=True,
        check=False,
    )

    assert resultado.returncode == 0, resultado.stderr

    dados = json.loads(resultado.stdout)

    assert dados["mensagens_raw"] == 1
    assert dados["processamentos_versao"] == 0
    assert dados["sem_estado_versao"] == 1
    assert dados["pendencias_observaveis"] == 1
