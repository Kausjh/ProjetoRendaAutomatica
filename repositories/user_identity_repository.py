from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from models.user_identity import ContaUsuario, SessaoUsuario


@dataclass(frozen=True, slots=True)
class CredencialConta:
    conta: ContaUsuario
    senha_salt: bytes
    senha_hash: bytes


class UserIdentityRepository:
    def __init__(self, caminho_banco: str | Path) -> None:
        self.caminho_banco = Path(caminho_banco)
        self.caminho_banco.parent.mkdir(parents=True, exist_ok=True)
        self._inicializar()

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(self.caminho_banco)
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA foreign_keys = ON")
        return conexao

    def _inicializar(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS contas_usuario (
                    id TEXT PRIMARY KEY,
                    email_normalizado TEXT NOT NULL UNIQUE,
                    email_exibicao TEXT NOT NULL,
                    senha_salt BLOB NOT NULL,
                    senha_hash BLOB NOT NULL,
                    criado_em TEXT NOT NULL,
                    ativa INTEGER NOT NULL DEFAULT 1
                        CHECK (ativa IN (0, 1))
                );

                CREATE TABLE IF NOT EXISTS sessoes_usuario (
                    id TEXT PRIMARY KEY,
                    conta_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    criado_em TEXT NOT NULL,
                    expira_em TEXT NOT NULL,
                    revogada_em TEXT,
                    FOREIGN KEY (conta_id)
                        REFERENCES contas_usuario(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_sessoes_usuario_conta
                    ON sessoes_usuario(conta_id);

                CREATE INDEX IF NOT EXISTS idx_sessoes_usuario_expira
                    ON sessoes_usuario(expira_em);
                """)

    def criar_conta(
        self,
        *,
        conta_id: str,
        email_normalizado: str,
        email_exibicao: str,
        senha_salt: bytes,
        senha_hash: bytes,
        criado_em: str,
    ) -> ContaUsuario:
        try:
            with self._conectar() as conexao:
                conexao.execute(
                    """
                    INSERT INTO contas_usuario (
                        id,
                        email_normalizado,
                        email_exibicao,
                        senha_salt,
                        senha_hash,
                        criado_em,
                        ativa
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    """,
                    (
                        conta_id,
                        email_normalizado,
                        email_exibicao,
                        senha_salt,
                        senha_hash,
                        criado_em,
                    ),
                )
        except sqlite3.IntegrityError as erro:
            if "email_normalizado" in str(erro).lower():
                raise ValueError("Ja existe uma conta para este email.") from erro
            raise

        return ContaUsuario(
            id=conta_id,
            email=email_exibicao,
            criado_em=criado_em,
            ativa=True,
        )

    def obter_credencial_por_email(
        self,
        email_normalizado: str,
    ) -> CredencialConta | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT
                    id,
                    email_exibicao,
                    senha_salt,
                    senha_hash,
                    criado_em,
                    ativa
                FROM contas_usuario
                WHERE email_normalizado = ?
                """,
                (email_normalizado,),
            ).fetchone()

        if linha is None:
            return None

        conta = ContaUsuario(
            id=str(linha["id"]),
            email=str(linha["email_exibicao"]),
            criado_em=str(linha["criado_em"]),
            ativa=bool(linha["ativa"]),
        )

        return CredencialConta(
            conta=conta,
            senha_salt=bytes(linha["senha_salt"]),
            senha_hash=bytes(linha["senha_hash"]),
        )

    def obter_conta(self, conta_id: str) -> ContaUsuario | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT id, email_exibicao, criado_em, ativa
                FROM contas_usuario
                WHERE id = ?
                """,
                (conta_id,),
            ).fetchone()

        if linha is None:
            return None

        return ContaUsuario(
            id=str(linha["id"]),
            email=str(linha["email_exibicao"]),
            criado_em=str(linha["criado_em"]),
            ativa=bool(linha["ativa"]),
        )

    def criar_sessao(
        self,
        *,
        sessao_id: str,
        conta_id: str,
        token_hash: str,
        criado_em: str,
        expira_em: str,
    ) -> SessaoUsuario:
        with self._conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO sessoes_usuario (
                    id,
                    conta_id,
                    token_hash,
                    criado_em,
                    expira_em,
                    revogada_em
                )
                VALUES (?, ?, ?, ?, ?, NULL)
                """,
                (
                    sessao_id,
                    conta_id,
                    token_hash,
                    criado_em,
                    expira_em,
                ),
            )

        return SessaoUsuario(
            id=sessao_id,
            conta_id=conta_id,
            criado_em=criado_em,
            expira_em=expira_em,
            revogada_em=None,
        )

    def obter_sessao_por_token_hash(
        self,
        token_hash: str,
    ) -> SessaoUsuario | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT id, conta_id, criado_em, expira_em, revogada_em
                FROM sessoes_usuario
                WHERE token_hash = ?
                """,
                (token_hash,),
            ).fetchone()

        if linha is None:
            return None

        return SessaoUsuario(
            id=str(linha["id"]),
            conta_id=str(linha["conta_id"]),
            criado_em=str(linha["criado_em"]),
            expira_em=str(linha["expira_em"]),
            revogada_em=(str(linha["revogada_em"]) if linha["revogada_em"] is not None else None),
        )

    def revogar_sessao(
        self,
        *,
        sessao_id: str,
        revogada_em: str,
    ) -> bool:
        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE sessoes_usuario
                SET revogada_em = ?
                WHERE id = ?
                  AND revogada_em IS NULL
                """,
                (revogada_em, sessao_id),
            )

        return cursor.rowcount == 1
