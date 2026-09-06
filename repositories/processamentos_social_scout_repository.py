# 63.8738, -149.7525

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from models.mensagem_social_scout import (
    MensagemSocialScout,
)


class ProcessamentosSocialScoutRepository:
    """
    Estado persistente do processamento das mensagens
    capturadas pelo Social Scout.

    O conteudo bruto continua em MensagensSocialScoutRepository.

    Esta tabela guarda somente:
    - identidade da mensagem;
    - versao do processador;
    - fingerprint;
    - status;
    - motivo.

    Nenhuma identidade do autor da mensagem e armazenada.
    """

    # status -> (cooldown entre tentativas, janela maxima)
    #
    # preco_rejeitado:
    #   preco, estoque e cupom podem mudar rapidamente.
    #
    # nao_resolvida:
    #   redirects/landing pages podem mudar, mas usamos
    #   intervalo maior para nao martelar links antigos.
    POLITICA_RETRY_SEGUNDOS = {
        "preco_rejeitado": (
            15 * 60,
            6 * 60 * 60,
        ),
        "nao_resolvida": (
            30 * 60,
            12 * 60 * 60,
        ),
    }

    def __init__(
        self,
        caminho_arquivo: str | Path = ("database/social_scout.sqlite3"),
    ) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)

        self.caminho_arquivo.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self._criar_estrutura()

    def _conectar(
        self,
    ) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            self.caminho_arquivo,
            timeout=15,
        )

        conexao.row_factory = sqlite3.Row

        conexao.execute("PRAGMA journal_mode=WAL")

        conexao.execute("PRAGMA synchronous=NORMAL")

        return conexao

    @contextmanager
    def _abrir_conexao(
        self,
    ):
        conexao = self._conectar()

        try:
            with conexao:
                yield conexao

        finally:
            conexao.close()

    def _criar_estrutura(
        self,
    ) -> None:
        with self._abrir_conexao() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS
                processamentos_social_scout (
                    fonte TEXT NOT NULL,
                    chat_id TEXT NOT NULL,
                    message_id INTEGER NOT NULL,

                    versao_processador TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,

                    status TEXT NOT NULL,
                    motivo TEXT NOT NULL DEFAULT '',

                    criado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    atualizado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,

                    PRIMARY KEY (
                        fonte,
                        chat_id,
                        message_id,
                        versao_processador
                    )
                );
                """)

    def obter(
        self,
        mensagem: MensagemSocialScout,
        versao_processador: str,
    ) -> dict | None:
        with self._abrir_conexao() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    fingerprint,
                    status,
                    motivo,
                    criado_em,
                    atualizado_em
                FROM processamentos_social_scout
                WHERE fonte = ?
                  AND chat_id = ?
                  AND message_id = ?
                  AND versao_processador = ?
                """,
                (
                    mensagem.fonte,
                    mensagem.chat_id,
                    mensagem.message_id,
                    str(versao_processador),
                ),
            ).fetchone()

        if linha is None:
            return None

        return {
            "fingerprint": str(linha["fingerprint"]),
            "status": str(linha["status"]),
            "motivo": str(linha["motivo"]),
            "criado_em": str(linha["criado_em"]),
            "atualizado_em": str(linha["atualizado_em"]),
        }

    def esta_processada(
        self,
        mensagem: MensagemSocialScout,
        versao_processador: str,
        fingerprint: str,
        *,
        agora_utc: datetime | None = None,
    ) -> bool:
        estado = self.obter(
            mensagem,
            versao_processador,
        )

        if estado is None:
            return False

        if estado["fingerprint"] != str(fingerprint):
            return False

        politica = self.POLITICA_RETRY_SEGUNDOS.get(estado["status"])

        # Status sem politica explicita continuam terminais.
        if politica is None:
            return True

        cooldown_segundos, janela_maxima_segundos = politica

        criado_em = self._parse_data_utc(estado["criado_em"])

        atualizado_em = self._parse_data_utc(estado["atualizado_em"])

        # Falha fechada:
        # timestamp inesperado nao deve causar loop de retry.
        if criado_em is None or atualizado_em is None:
            return True

        agora = agora_utc if agora_utc is not None else datetime.now(UTC)

        agora = self._normalizar_data_utc(agora)

        idade_total = (agora - criado_em).total_seconds()

        desde_ultima_tentativa = (agora - atualizado_em).total_seconds()

        # A janela total esgotou:
        # passa a ser terminal para este fingerprint.
        if idade_total >= janela_maxima_segundos:
            return True

        # Ainda esta em cooldown.
        if desde_ultima_tentativa < cooldown_segundos:
            return True

        # Cooldown venceu e a janela total continua aberta.
        return False

    @staticmethod
    def _normalizar_data_utc(
        valor: datetime,
    ) -> datetime:
        if valor.tzinfo is None:
            return valor.replace(tzinfo=UTC)

        return valor.astimezone(UTC)

    @classmethod
    def _parse_data_utc(
        cls,
        valor: str,
    ) -> datetime | None:
        texto = str(valor or "").strip()

        if not texto:
            return None

        if texto.endswith("Z"):
            texto = texto[:-1] + "+00:00"

        try:
            resultado = datetime.fromisoformat(texto)

        except ValueError:
            return None

        return cls._normalizar_data_utc(resultado)

    def salvar(
        self,
        mensagem: MensagemSocialScout,
        versao_processador: str,
        fingerprint: str,
        status: str,
        motivo: str = "",
    ) -> None:
        with self._abrir_conexao() as conexao:
            conexao.execute(
                """
                INSERT INTO processamentos_social_scout (
                    fonte,
                    chat_id,
                    message_id,
                    versao_processador,
                    fingerprint,
                    status,
                    motivo
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT (
                    fonte,
                    chat_id,
                    message_id,
                    versao_processador
                )
                DO UPDATE SET
                    criado_em = CASE
                        WHEN
                            processamentos_social_scout.fingerprint
                            <> excluded.fingerprint
                        THEN CURRENT_TIMESTAMP
                        ELSE processamentos_social_scout.criado_em
                    END,
                    fingerprint = excluded.fingerprint,
                    status = excluded.status,
                    motivo = excluded.motivo,
                    atualizado_em = CURRENT_TIMESTAMP
                """,
                (
                    mensagem.fonte,
                    mensagem.chat_id,
                    mensagem.message_id,
                    str(versao_processador),
                    str(fingerprint),
                    str(status),
                    str(motivo),
                ),
            )

    def quantidade(
        self,
    ) -> int:
        with self._abrir_conexao() as conexao:
            linha = conexao.execute("""
                SELECT COUNT(*) AS total
                FROM processamentos_social_scout
                """).fetchone()

        return int(linha["total"])
