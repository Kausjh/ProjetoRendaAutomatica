from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path

from models.push_dispatcher import ReciboPushExpo, RegistroTentativaPush, TicketPushExpo

_MAX_ERRO = 500


class PushDeliveryRepository:
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
                CREATE TABLE IF NOT EXISTS push_delivery_attempts (
                    id TEXT PRIMARY KEY,
                    outbox_id TEXT NOT NULL,
                    dispositivo_id TEXT NOT NULL,
                    outbox_tentativa INTEGER NOT NULL DEFAULT 1
                        CHECK (outbox_tentativa >= 1),
                    ticket_id TEXT UNIQUE,
                    ticket_status TEXT NOT NULL
                        CHECK (ticket_status IN ('ok', 'error')),
                    receipt_status TEXT
                        CHECK (
                            receipt_status IS NULL
                            OR receipt_status IN ('ok', 'error')
                        ),
                    provider_error_code TEXT,
                    ultimo_erro TEXT,
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    FOREIGN KEY (outbox_id)
                        REFERENCES personalized_notification_outbox(id)
                        ON DELETE CASCADE,
                    FOREIGN KEY (dispositivo_id)
                        REFERENCES dispositivos_usuario(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_push_delivery_outbox
                    ON push_delivery_attempts(outbox_id, criado_em);

                CREATE INDEX IF NOT EXISTS idx_push_delivery_receipts
                    ON push_delivery_attempts(
                        ticket_status,
                        receipt_status,
                        atualizado_em
                    );
            """)

            colunas = {
                str(linha[1])
                for linha in conexao.execute("PRAGMA table_info(push_delivery_attempts)").fetchall()
            }
            if "outbox_tentativa" not in colunas:
                conexao.execute(
                    "ALTER TABLE push_delivery_attempts "
                    "ADD COLUMN outbox_tentativa INTEGER NOT NULL DEFAULT 1"
                )

    @staticmethod
    def _agora() -> str:
        return datetime.now(UTC).isoformat()

    @staticmethod
    def _erro(valor: str | None) -> str | None:
        if valor is None:
            return None
        texto = str(valor).strip()
        return texto[:_MAX_ERRO] if texto else None

    @staticmethod
    def _da_linha(linha: sqlite3.Row) -> RegistroTentativaPush:
        return RegistroTentativaPush(
            id=str(linha["id"]),
            outbox_id=str(linha["outbox_id"]),
            dispositivo_id=str(linha["dispositivo_id"]),
            outbox_tentativa=int(linha["outbox_tentativa"]),
            ticket_id=(str(linha["ticket_id"]) if linha["ticket_id"] is not None else None),
            ticket_status=str(linha["ticket_status"]),
            receipt_status=(
                str(linha["receipt_status"]) if linha["receipt_status"] is not None else None
            ),
            provider_error_code=(
                str(linha["provider_error_code"])
                if linha["provider_error_code"] is not None
                else None
            ),
            ultimo_erro=(str(linha["ultimo_erro"]) if linha["ultimo_erro"] is not None else None),
            criado_em=str(linha["criado_em"]),
            atualizado_em=str(linha["atualizado_em"]),
        )

    def registrar_ticket(
        self,
        *,
        outbox_id: str,
        dispositivo_id: str,
        ticket: TicketPushExpo,
        outbox_tentativa: int = 1,
    ) -> RegistroTentativaPush:
        if ticket.status not in {"ok", "error"}:
            raise ValueError("ticket_status invalido.")

        tentativa_outbox = int(outbox_tentativa)
        if tentativa_outbox < 1:
            raise ValueError("outbox_tentativa precisa ser positiva.")

        if ticket.status == "ok" and not ticket.ticket_id:
            raise ValueError("Ticket ok precisa de ticket_id.")

        agora = self._agora()
        tentativa_id = f"pda_{uuid.uuid4().hex}"

        with self._conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO push_delivery_attempts (
                    id, outbox_id, dispositivo_id, outbox_tentativa,
                    ticket_id, ticket_status, receipt_status,
                    provider_error_code, ultimo_erro, criado_em, atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?)
                """,
                (
                    tentativa_id,
                    outbox_id,
                    dispositivo_id,
                    tentativa_outbox,
                    ticket.ticket_id,
                    ticket.status,
                    ticket.erro_codigo,
                    self._erro(ticket.erro_mensagem),
                    agora,
                    agora,
                ),
            )

        tentativa = self.obter_por_id(tentativa_id)
        if tentativa is None:
            raise RuntimeError("Tentativa push desapareceu apos persistencia.")
        return tentativa

    def registrar_recibo(self, recibo: ReciboPushExpo) -> RegistroTentativaPush:
        if recibo.status not in {"ok", "error"}:
            raise ValueError("receipt_status invalido.")

        agora = self._agora()

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE push_delivery_attempts
                SET receipt_status = ?, provider_error_code = ?,
                    ultimo_erro = ?, atualizado_em = ?
                WHERE ticket_id = ?
                  AND ticket_status = 'ok'
                """,
                (
                    recibo.status,
                    recibo.erro_codigo,
                    self._erro(recibo.erro_mensagem),
                    agora,
                    recibo.ticket_id,
                ),
            )

        if cursor.rowcount != 1:
            raise ValueError("Receipt sem ticket pendente correspondente.")

        tentativa = self.obter_por_ticket(recibo.ticket_id)
        if tentativa is None:
            raise RuntimeError("Tentativa push desapareceu apos receipt.")
        return tentativa

    def listar_aguardando_recibo(
        self,
        *,
        limite: int = 1000,
        criado_ate: str | None = None,
    ) -> list[RegistroTentativaPush]:
        limite_seguro = max(1, min(int(limite), 1000))
        corte = str(criado_ate or "").strip() or None
        filtro_corte = " AND criado_em <= ?" if corte is not None else ""

        parametros: tuple[object, ...]
        if corte is None:
            parametros = (limite_seguro,)
        else:
            parametros = (corte, limite_seguro)

        with self._conectar() as conexao:
            linhas = conexao.execute(
                f"""
                SELECT *
                FROM push_delivery_attempts
                WHERE ticket_status = 'ok'
                  AND receipt_status IS NULL
                  AND ticket_id IS NOT NULL
                  {filtro_corte}
                ORDER BY criado_em ASC, id ASC
                LIMIT ?
                """,
                parametros,
            ).fetchall()

        return [self._da_linha(linha) for linha in linhas]

    def listar_por_outbox(
        self,
        outbox_id: str,
        *,
        limite: int = 100,
    ) -> list[RegistroTentativaPush]:
        limite_seguro = max(1, min(int(limite), 500))

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM push_delivery_attempts
                WHERE outbox_id = ?
                ORDER BY criado_em ASC, id ASC
                LIMIT ?
                """,
                (str(outbox_id or "").strip(), limite_seguro),
            ).fetchall()

        return [self._da_linha(linha) for linha in linhas]

    def obter_por_id(self, tentativa_id: str) -> RegistroTentativaPush | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT * FROM push_delivery_attempts WHERE id = ?",
                (tentativa_id,),
            ).fetchone()
        return self._da_linha(linha) if linha is not None else None

    def obter_por_ticket(self, ticket_id: str) -> RegistroTentativaPush | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                "SELECT * FROM push_delivery_attempts WHERE ticket_id = ?",
                (ticket_id,),
            ).fetchone()
        return self._da_linha(linha) if linha is not None else None
