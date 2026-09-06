# 63.8738, -149.7525

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class MetricasSocialScout:
    versao_processador: str
    mensagens_raw: int
    processamentos_total: int
    processamentos_versao: int
    sem_estado_versao: int
    raw_atualizadas_depois_estado: int
    pendencias_observaveis: int
    cobertura_percentual: float
    status: dict[str, int]
    candidatas_sombra: int
    sombra_nicho: int
    sombra_fora_nicho: int
    taxa_nicho_sombra_percentual: float | None
    primeira_mensagem_em: str | None
    ultima_mensagem_atualizada_em: str | None
    primeiro_processamento_em: str | None
    ultimo_processamento_atualizado_em: str | None

    def para_dict(self) -> dict[str, Any]:
        return asdict(self)


def _abrir_read_only(
    caminho: str | Path,
) -> sqlite3.Connection:
    caminho_db = Path(caminho)

    if not caminho_db.exists():
        raise FileNotFoundError(f"Banco Social Scout nao encontrado: {caminho_db}")

    uri = caminho_db.resolve().as_uri() + "?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=5.0,
    )


def _quantidade(
    conexao: sqlite3.Connection,
    sql: str,
    parametros: tuple[Any, ...] = (),
) -> int:
    linha = conexao.execute(
        sql,
        parametros,
    ).fetchone()

    if linha is None:
        return 0

    return int(linha[0] or 0)


def coletar_metricas(
    caminho: str | Path = "database/social_scout.sqlite3",
    *,
    versao_processador: str,
) -> MetricasSocialScout:
    conexao = _abrir_read_only(caminho)

    try:
        tabelas = {linha[0] for linha in conexao.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """)}

        obrigatorias = {
            "mensagens_social_scout",
            "processamentos_social_scout",
        }

        faltantes = obrigatorias - tabelas

        if faltantes:
            raise RuntimeError(
                "Banco Social Scout sem tabela(s) obrigatoria(s): " + ", ".join(sorted(faltantes))
            )

        mensagens_raw = _quantidade(
            conexao,
            """
            SELECT COUNT(*)
            FROM mensagens_social_scout
            """,
        )

        processamentos_total = _quantidade(
            conexao,
            """
            SELECT COUNT(*)
            FROM processamentos_social_scout
            """,
        )

        processamentos_versao = _quantidade(
            conexao,
            """
            SELECT COUNT(*)
            FROM processamentos_social_scout
            WHERE versao_processador = ?
            """,
            (versao_processador,),
        )

        sem_estado_versao = _quantidade(
            conexao,
            """
            SELECT COUNT(*)
            FROM mensagens_social_scout AS m
            LEFT JOIN processamentos_social_scout AS p
                ON p.fonte = m.fonte
               AND p.chat_id = m.chat_id
               AND p.message_id = m.message_id
               AND p.versao_processador = ?
            WHERE p.message_id IS NULL
            """,
            (versao_processador,),
        )

        raw_atualizadas_depois_estado = _quantidade(
            conexao,
            """
            SELECT COUNT(*)
            FROM mensagens_social_scout AS m
            INNER JOIN processamentos_social_scout AS p
                ON p.fonte = m.fonte
               AND p.chat_id = m.chat_id
               AND p.message_id = m.message_id
               AND p.versao_processador = ?
            WHERE
                COALESCE(
                    m.atualizado_em,
                    m.criado_em
                )
                >
                COALESCE(
                    p.atualizado_em,
                    p.criado_em
                )
            """,
            (versao_processador,),
        )

        pendencias_observaveis = sem_estado_versao + raw_atualizadas_depois_estado

        if mensagens_raw > 0:
            cobertura_percentual = round(
                (processamentos_versao / mensagens_raw) * 100.0,
                2,
            )
        else:
            cobertura_percentual = 100.0

        status = {
            str(status_nome): int(total)
            for status_nome, total in conexao.execute(
                """
                SELECT
                    status,
                    COUNT(*)
                FROM processamentos_social_scout
                WHERE versao_processador = ?
                GROUP BY status
                ORDER BY status
                """,
                (versao_processador,),
            ).fetchall()
        }

        sombra_nicho = status.get(
            "sombra_nicho",
            0,
        )

        sombra_fora_nicho = status.get(
            "sombra_fora_nicho",
            0,
        )

        candidatas_sombra = sombra_nicho + sombra_fora_nicho

        if candidatas_sombra > 0:
            taxa_nicho = round(
                (sombra_nicho / candidatas_sombra) * 100.0,
                2,
            )
        else:
            taxa_nicho = None

        temporal_mensagens = conexao.execute("""
                SELECT
                    MIN(criado_em),
                    MAX(
                        COALESCE(
                            atualizado_em,
                            criado_em
                        )
                    )
                FROM mensagens_social_scout
                """).fetchone()

        temporal_processamentos = conexao.execute(
            """
                SELECT
                    MIN(criado_em),
                    MAX(
                        COALESCE(
                            atualizado_em,
                            criado_em
                        )
                    )
                FROM processamentos_social_scout
                WHERE versao_processador = ?
                """,
            (versao_processador,),
        ).fetchone()

        return MetricasSocialScout(
            versao_processador=versao_processador,
            mensagens_raw=mensagens_raw,
            processamentos_total=processamentos_total,
            processamentos_versao=processamentos_versao,
            sem_estado_versao=sem_estado_versao,
            raw_atualizadas_depois_estado=(raw_atualizadas_depois_estado),
            pendencias_observaveis=(pendencias_observaveis),
            cobertura_percentual=(cobertura_percentual),
            status=status,
            candidatas_sombra=candidatas_sombra,
            sombra_nicho=sombra_nicho,
            sombra_fora_nicho=(sombra_fora_nicho),
            taxa_nicho_sombra_percentual=(taxa_nicho),
            primeira_mensagem_em=(temporal_mensagens[0] if temporal_mensagens else None),
            ultima_mensagem_atualizada_em=(temporal_mensagens[1] if temporal_mensagens else None),
            primeiro_processamento_em=(
                temporal_processamentos[0] if temporal_processamentos else None
            ),
            ultimo_processamento_atualizado_em=(
                temporal_processamentos[1] if temporal_processamentos else None
            ),
        )

    finally:
        conexao.close()


def formatar_relatorio(
    metricas: MetricasSocialScout,
) -> str:
    linhas = [
        "=" * 72,
        "SOCIAL SCOUT - OBSERVABILIDADE",
        "=" * 72,
        ("Versao do processador: " f"{metricas.versao_processador}"),
        ("Mensagens raw: " f"{metricas.mensagens_raw}"),
        ("Processamentos totais: " f"{metricas.processamentos_total}"),
        ("Processamentos da versao atual: " f"{metricas.processamentos_versao}"),
        ("Cobertura da versao atual: " f"{metricas.cobertura_percentual:.2f}%"),
        ("Sem estado na versao atual: " f"{metricas.sem_estado_versao}"),
        ("Raw atualizadas apos o estado: " f"{metricas.raw_atualizadas_depois_estado}"),
        ("Pendencias observaveis: " f"{metricas.pendencias_observaveis}"),
        "",
        "SHADOW:",
        ("  candidatas classificadas: " f"{metricas.candidatas_sombra}"),
        ("  dentro do nicho: " f"{metricas.sombra_nicho}"),
        ("  fora do nicho: " f"{metricas.sombra_fora_nicho}"),
    ]

    if metricas.taxa_nicho_sombra_percentual is None:
        linhas.append("  taxa de nicho: n/a")

    else:
        linhas.append("  taxa de nicho: " f"{metricas.taxa_nicho_sombra_percentual:.2f}%")

    linhas.extend(
        [
            "",
            "STATUS:",
        ]
    )

    if metricas.status:
        for nome, quantidade in sorted(metricas.status.items()):
            linhas.append(f"  {nome}: {quantidade}")

    else:
        linhas.append("  nenhum processamento")

    linhas.extend(
        [
            "",
            "INTERVALO:",
            ("  primeira mensagem: " f"{metricas.primeira_mensagem_em or 'n/a'}"),
            ("  ultima atualizacao raw: " f"{metricas.ultima_mensagem_atualizada_em or 'n/a'}"),
            ("  primeiro processamento: " f"{metricas.primeiro_processamento_em or 'n/a'}"),
            ("  ultimo processamento: " f"{metricas.ultimo_processamento_atualizado_em or 'n/a'}"),
            "=" * 72,
        ]
    )

    return "\n".join(linhas)
