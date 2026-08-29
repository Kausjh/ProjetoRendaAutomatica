# 63.8738, -149.7525

from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from models.oferta import Oferta
from services.historico_precos_service import ResultadoHistoricoPreco
from services.identificador_familia_produto import IdentificadorFamiliaProduto

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ItemFilaPublicacao:
    id: int
    oferta: Oferta
    resultado_historico: ResultadoHistoricoPreco | None
    pontuacao: float
    deve_republicar_por_queda: bool
    prioridade: float
    criado_em: datetime
    atualizado_em: datetime
    status: str
    segurado_ate: datetime | None = None
    agendado_para: datetime | None = None
    aprovado_manualmente: bool = False


class FilaPublicacaoRepository:
    """Fila persistente e concorrente baseada em SQLite.

    Pipeline e publicador rodam em processos diferentes. SQLite evita
    corrupção do arquivo quando ambos acessam a fila ao mesmo tempo.
    """

    def __init__(
        self,
        caminho_arquivo: str = "database/fila_publicacao.sqlite3",
    ) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)
        self.caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)
        self.identificador_familia = IdentificadorFamiliaProduto()
        self._criar_estrutura()

    def _conectar(self) -> sqlite3.Connection:
        conexao = sqlite3.connect(
            self.caminho_arquivo,
            timeout=15,
        )
        conexao.row_factory = sqlite3.Row
        conexao.execute("PRAGMA journal_mode=WAL")
        conexao.execute("PRAGMA synchronous=NORMAL")
        return conexao

    def _criar_estrutura(self) -> None:
        with self._conectar() as conexao:
            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS fila_publicacao (
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
                    segurado_ate TEXT,
                    agendado_para TEXT,
                    aprovado_manualmente INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'pendente',
                    criado_em TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL,
                    publicado_em TEXT,
                    motivo_saida TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_fila_status_prioridade
                ON fila_publicacao(status, prioridade DESC, criado_em ASC);

                CREATE INDEX IF NOT EXISTS idx_fila_chave_status
                ON fila_publicacao(chave_canonica, status);

                CREATE INDEX IF NOT EXISTS idx_fila_familia_status
                ON fila_publicacao(chave_familia, status);

                CREATE INDEX IF NOT EXISTS idx_fila_publicado_em
                ON fila_publicacao(publicado_em);
                """)

            colunas = {
                linha["name"]
                for linha in conexao.execute("PRAGMA table_info(fila_publicacao)").fetchall()
            }

            migracoes = {
                "chave_familia": "TEXT",
                "familia": "TEXT",
                "confianca_familia": "REAL NOT NULL DEFAULT 0",
                "segurado_ate": "TEXT",
                "agendado_para": "TEXT",
                "aprovado_manualmente": "INTEGER NOT NULL DEFAULT 0",
            }

            for coluna, tipo in migracoes.items():
                if coluna not in colunas:
                    conexao.execute(f"ALTER TABLE fila_publicacao ADD COLUMN {coluna} {tipo}")

            conexao.execute("""
                CREATE INDEX IF NOT EXISTS idx_fila_familia_status
                ON fila_publicacao(chave_familia, status)
                """)

            conexao.execute("""
                CREATE INDEX IF NOT EXISTS idx_fila_agenda
                ON fila_publicacao(status, agendado_para, segurado_ate)
                """)

            conexao.execute("""
                CREATE TABLE IF NOT EXISTS controle_publicacao (
                    chave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL,
                    atualizado_em TEXT NOT NULL
                )
                """)

            conexao.executescript("""
                CREATE TABLE IF NOT EXISTS historico_publicacoes_fila (
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

                CREATE UNIQUE INDEX IF NOT EXISTS idx_historico_publicacao_evento
                ON historico_publicacoes_fila(fila_item_id, publicado_em, oferta_json);

                CREATE INDEX IF NOT EXISTS idx_historico_publicacao_link
                ON historico_publicacoes_fila(link, publicado_em DESC);

                CREATE INDEX IF NOT EXISTS idx_historico_publicacao_data
                ON historico_publicacoes_fila(publicado_em DESC);
                """)

            conexao.execute("""
                INSERT OR IGNORE INTO historico_publicacoes_fila (
                    fila_item_id,
                    link,
                    chave_canonica,
                    chave_familia,
                    familia,
                    categoria,
                    marca,
                    tipo_oportunidade,
                    oferta_json,
                    pontuacao,
                    publicado_em
                )
                SELECT
                    id,
                    link,
                    chave_canonica,
                    chave_familia,
                    familia,
                    categoria,
                    marca,
                    tipo_oportunidade,
                    oferta_json,
                    pontuacao,
                    publicado_em
                FROM fila_publicacao
                WHERE publicado_em IS NOT NULL
                """)

    def adicionar_ou_atualizar(
        self,
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None,
        pontuacao: float,
        deve_republicar_por_queda: bool,
        prioridade: float,
        permitir_republicacao: bool = False,
    ) -> str:
        agora = datetime.now().astimezone()
        agora_iso = agora.isoformat(timespec="seconds")

        resultado_familia = self.identificador_familia.identificar(oferta)

        logger.debug(
            ("Família identificada: %s | chave=%s | confiança=%.1f | " "produto=%s"),
            resultado_familia.nome_familia,
            resultado_familia.chave_familia,
            resultado_familia.confianca,
            oferta.nome,
        )

        oferta_json = json.dumps(asdict(oferta), ensure_ascii=False)
        historico_json = (
            json.dumps(asdict(resultado_historico), ensure_ascii=False)
            if resultado_historico is not None
            else None
        )

        with self._conectar() as conexao:
            existente = conexao.execute(
                """
                SELECT id, status, prioridade
                FROM fila_publicacao
                WHERE link = ?
                """,
                (oferta.link,),
            ).fetchone()

            if existente is not None:
                status_existente = str(existente["status"])

                if status_existente == "publicado" and not permitir_republicacao:
                    return "ja_publicado_pela_fila"

                reativando = status_existente != "pendente"

                conexao.execute(
                    """
                    UPDATE fila_publicacao
                    SET
                        chave_canonica = ?,
                        chave_familia = ?,
                        familia = ?,
                        confianca_familia = ?,
                        categoria = ?,
                        marca = ?,
                        tipo_oportunidade = ?,
                        oferta_json = ?,
                        historico_json = ?,
                        pontuacao = ?,
                        prioridade = ?,
                        deve_republicar_por_queda = ?,
                        segurado_ate = CASE
                            WHEN status = 'pendente' THEN segurado_ate
                            ELSE NULL
                        END,
                        agendado_para = CASE
                            WHEN status = 'pendente' THEN agendado_para
                            ELSE NULL
                        END,
                        aprovado_manualmente = CASE
                            WHEN status = 'pendente' THEN aprovado_manualmente
                            ELSE 0
                        END,
                        status = 'pendente',
                        criado_em = CASE
                            WHEN status = 'pendente' THEN criado_em
                            ELSE ?
                        END,
                        atualizado_em = ?,
                        publicado_em = CASE
                            WHEN status = 'pendente' THEN publicado_em
                            ELSE NULL
                        END,
                        motivo_saida = NULL
                    WHERE id = ?
                    """,
                    (
                        oferta.chave_produto_canonica,
                        oferta.chave_familia_produto,
                        oferta.familia_produto,
                        oferta.confianca_familia,
                        oferta.categoria,
                        oferta.marca,
                        oferta.tipo_oportunidade,
                        oferta_json,
                        historico_json,
                        pontuacao,
                        prioridade,
                        int(deve_republicar_por_queda),
                        agora_iso,
                        agora_iso,
                        existente["id"],
                    ),
                )

                if not reativando:
                    return "atualizado"

                if status_existente == "publicado":
                    if deve_republicar_por_queda:
                        return "reativado_por_queda"
                    return "reativado_por_tempo"

                return "reativado"

            substituido = self._substituir_canonico_se_melhor(
                conexao=conexao,
                oferta=oferta,
                resultado_historico=resultado_historico,
                pontuacao=pontuacao,
                prioridade=prioridade,
                deve_republicar_por_queda=deve_republicar_por_queda,
                agora_iso=agora_iso,
                oferta_json=oferta_json,
                historico_json=historico_json,
            )

            if substituido:
                return "substituido_canonico"

            substituido_familia = self._substituir_familia_se_melhor(
                conexao=conexao,
                oferta=oferta,
                resultado_historico=resultado_historico,
                pontuacao=pontuacao,
                prioridade=prioridade,
                deve_republicar_por_queda=deve_republicar_por_queda,
                agora_iso=agora_iso,
                oferta_json=oferta_json,
                historico_json=historico_json,
            )

            if substituido_familia:
                return "substituido_familia"

            conexao.execute(
                """
                INSERT INTO fila_publicacao (
                    link,
                    chave_canonica,
                    chave_familia,
                    familia,
                    confianca_familia,
                    categoria,
                    marca,
                    tipo_oportunidade,
                    oferta_json,
                    historico_json,
                    pontuacao,
                    prioridade,
                    deve_republicar_por_queda,
                    status,
                    criado_em,
                    atualizado_em
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendente', ?, ?)
                """,
                (
                    oferta.link,
                    oferta.chave_produto_canonica,
                    oferta.chave_familia_produto,
                    oferta.familia_produto,
                    oferta.confianca_familia,
                    oferta.categoria,
                    oferta.marca,
                    oferta.tipo_oportunidade,
                    oferta_json,
                    historico_json,
                    pontuacao,
                    prioridade,
                    int(deve_republicar_por_queda),
                    agora_iso,
                    agora_iso,
                ),
            )

        return "adicionado"

    @staticmethod
    def _chave_marketplace_oferta(
        oferta: Oferta,
    ) -> str:
        valor = getattr(oferta, "marketplace", None) or getattr(oferta, "loja", None)

        if not isinstance(valor, str):
            return ""

        chave = valor.strip().casefold()

        if "shopee" in chave:
            return "shopee"

        if "mercado" in chave and "livre" in chave:
            return "mercado_livre"

        return chave.replace(" ", "_")

    def _substituir_canonico_se_melhor(
        self,
        conexao: sqlite3.Connection,
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None,
        pontuacao: float,
        prioridade: float,
        deve_republicar_por_queda: bool,
        agora_iso: str,
        oferta_json: str,
        historico_json: str | None,
    ) -> bool:
        chave = oferta.chave_produto_canonica

        if not chave or oferta.confianca_normalizacao < 90:
            return False

        existentes = conexao.execute(
            """
            SELECT id, prioridade, oferta_json
            FROM fila_publicacao
            WHERE chave_canonica = ?
              AND status = 'pendente'
            ORDER BY prioridade DESC
            """,
            (chave,),
        ).fetchall()

        marketplace_novo = self._chave_marketplace_oferta(oferta)

        existente = None

        for candidato in existentes:
            try:
                oferta_existente = Oferta(**json.loads(candidato["oferta_json"]))
            except Exception:
                continue

            marketplace_existente = self._chave_marketplace_oferta(oferta_existente)

            if marketplace_existente == marketplace_novo:
                existente = candidato
                break

        if existente is None:
            return False

        if float(existente["prioridade"]) >= prioridade:
            return True

        conexao.execute(
            """
            UPDATE fila_publicacao
            SET
                link = ?,
                categoria = ?,
                marca = ?,
                tipo_oportunidade = ?,
                oferta_json = ?,
                historico_json = ?,
                pontuacao = ?,
                prioridade = ?,
                deve_republicar_por_queda = ?,
                atualizado_em = ?,
                motivo_saida = NULL
            WHERE id = ?
            """,
            (
                oferta.link,
                oferta.categoria,
                oferta.marca,
                oferta.tipo_oportunidade,
                oferta_json,
                historico_json,
                pontuacao,
                prioridade,
                int(deve_republicar_por_queda),
                agora_iso,
                existente["id"],
            ),
        )
        return True

    def _substituir_familia_se_melhor(
        self,
        conexao: sqlite3.Connection,
        oferta: Oferta,
        resultado_historico: ResultadoHistoricoPreco | None,
        pontuacao: float,
        prioridade: float,
        deve_republicar_por_queda: bool,
        agora_iso: str,
        oferta_json: str,
        historico_json: str | None,
    ) -> bool:
        chave = oferta.chave_familia_produto

        if not chave or oferta.confianca_familia < 80:
            return False

        existentes = conexao.execute(
            """
            SELECT id, prioridade, oferta_json
            FROM fila_publicacao
            WHERE chave_familia = ?
              AND status = 'pendente'
            ORDER BY prioridade DESC
            """,
            (chave,),
        ).fetchall()

        marketplace_novo = self._chave_marketplace_oferta(oferta)

        existente = None

        for candidato in existentes:
            try:
                oferta_existente_candidata = Oferta(**json.loads(candidato["oferta_json"]))
            except Exception:
                continue

            marketplace_existente = self._chave_marketplace_oferta(oferta_existente_candidata)

            if marketplace_existente == marketplace_novo:
                existente = candidato
                break

        if existente is None:
            return False

        oferta_existente = Oferta(**json.loads(existente["oferta_json"]))

        logger.debug(
            (
                "Família semântica detectada: %s | variante atual: '%s' "
                "(R$ %.2f) | nova variante: '%s' (R$ %.2f)"
            ),
            oferta.familia_produto or chave,
            oferta_existente.nome,
            float(oferta_existente.preco),
            oferta.nome,
            float(oferta.preco),
        )

        # Dentro da mesma família, preço é o critério principal.
        # Score só desempata ofertas com preço praticamente igual.
        preco_novo = float(oferta.preco)
        preco_existente = float(oferta_existente.preco)

        novo_melhor = preco_novo < preco_existente or (
            abs(preco_novo - preco_existente) < 0.01 and prioridade > float(existente["prioridade"])
        )

        if not novo_melhor:
            logger.debug(
                (
                    "Anti-duplicata de família: variante descartada '%s' "
                    "(R$ %.2f). Representante mantido: '%s' (R$ %.2f)."
                ),
                oferta.nome,
                preco_novo,
                oferta_existente.nome,
                preco_existente,
            )
            return True

        logger.debug(
            ("Anti-duplicata de família: representante trocado. " "'%s' R$ %.2f -> '%s' R$ %.2f."),
            oferta_existente.nome,
            preco_existente,
            oferta.nome,
            preco_novo,
        )

        conexao.execute(
            """
            UPDATE fila_publicacao
            SET
                link = ?,
                chave_canonica = ?,
                chave_familia = ?,
                familia = ?,
                confianca_familia = ?,
                categoria = ?,
                marca = ?,
                tipo_oportunidade = ?,
                oferta_json = ?,
                historico_json = ?,
                pontuacao = ?,
                prioridade = ?,
                deve_republicar_por_queda = ?,
                atualizado_em = ?,
                motivo_saida = NULL
            WHERE id = ?
            """,
            (
                oferta.link,
                oferta.chave_produto_canonica,
                oferta.chave_familia_produto,
                oferta.familia_produto,
                oferta.confianca_familia,
                oferta.categoria,
                oferta.marca,
                oferta.tipo_oportunidade,
                oferta_json,
                historico_json,
                pontuacao,
                prioridade,
                int(deve_republicar_por_queda),
                agora_iso,
                existente["id"],
            ),
        )
        return True

    def listar_pendentes(self, limite: int = 100) -> list[ItemFilaPublicacao]:
        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT *
                FROM fila_publicacao
                WHERE status = 'pendente'
                ORDER BY prioridade DESC, criado_em ASC
                LIMIT ?
                """,
                (limite,),
            ).fetchall()

        return [self._converter_linha(linha) for linha in linhas]

    def resumo_familias_pendentes(self) -> dict[str, int]:
        with self._conectar() as conexao:
            linha = conexao.execute("""
                SELECT
                    COUNT(*) AS itens,
                    COUNT(DISTINCT CASE
                        WHEN chave_familia IS NOT NULL
                         AND TRIM(chave_familia) <> ''
                        THEN chave_familia
                    END) AS familias,
                    SUM(CASE
                        WHEN chave_familia IS NOT NULL
                         AND TRIM(chave_familia) <> ''
                        THEN 1 ELSE 0
                    END) AS itens_com_familia
                FROM fila_publicacao
                WHERE status = 'pendente'
                """).fetchone()

        return {
            "itens": int(linha["itens"] or 0),
            "familias": int(linha["familias"] or 0),
            "itens_com_familia": int(linha["itens_com_familia"] or 0),
        }

    def quantidade_pendente(self) -> int:
        with self._conectar() as conexao:
            linha = conexao.execute("""
                SELECT COUNT(*) AS quantidade
                FROM fila_publicacao
                WHERE status = 'pendente'
                """).fetchone()

        return int(linha["quantidade"])

    def marcar_publicado(self, item_id: int) -> None:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    status = 'publicado',
                    publicado_em = ?,
                    atualizado_em = ?,
                    segurado_ate = NULL,
                    agendado_para = NULL,
                    aprovado_manualmente = 0,
                    motivo_saida = NULL
                WHERE id = ?
                """,
                (agora, agora, item_id),
            )

            conexao.execute(
                """
                INSERT OR IGNORE INTO historico_publicacoes_fila (
                    fila_item_id,
                    link,
                    chave_canonica,
                    chave_familia,
                    familia,
                    categoria,
                    marca,
                    tipo_oportunidade,
                    oferta_json,
                    pontuacao,
                    publicado_em
                )
                SELECT
                    id,
                    link,
                    chave_canonica,
                    chave_familia,
                    familia,
                    categoria,
                    marca,
                    tipo_oportunidade,
                    oferta_json,
                    pontuacao,
                    publicado_em
                FROM fila_publicacao
                WHERE id = ?
                  AND status = 'publicado'
                  AND publicado_em IS NOT NULL
                """,
                (item_id,),
            )

    def marcar_descartado(self, item_id: int, motivo: str) -> None:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    status = 'descartado',
                    atualizado_em = ?,
                    segurado_ate = NULL,
                    agendado_para = NULL,
                    aprovado_manualmente = 0,
                    motivo_saida = ?
                WHERE id = ?
                """,
                (agora, motivo, item_id),
            )

    def expirar_antigos(self, idade_maxima_minutos: float) -> int:
        agora = datetime.now().astimezone()
        limite = agora - timedelta(minutes=idade_maxima_minutos)
        limite_iso = limite.isoformat(timespec="seconds")
        agora_iso = agora.isoformat(timespec="seconds")

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    status = 'expirado',
                    atualizado_em = ?,
                    motivo_saida = 'Oferta ficou antiga demais na fila.'
                WHERE status = 'pendente'
                  AND criado_em < ?
                  AND agendado_para IS NULL
                  AND (
                      segurado_ate IS NULL
                      OR segurado_ate <= ?
                  )
                """,
                (agora_iso, limite_iso, agora_iso),
            )

        return int(cursor.rowcount)

    def reduzir_fila(self, tamanho_maximo: int) -> int:
        quantidade = self.quantidade_pendente()

        if quantidade <= tamanho_maximo:
            return 0

        remover = quantidade - tamanho_maximo
        agora_iso = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            ids = conexao.execute(
                """
                SELECT id
                FROM fila_publicacao
                WHERE status = 'pendente'
                  AND agendado_para IS NULL
                  AND (
                      segurado_ate IS NULL
                      OR segurado_ate <= ?
                  )
                ORDER BY prioridade ASC, criado_em ASC
                LIMIT ?
                """,
                (agora_iso, remover),
            ).fetchall()

            ids_numericos = [int(linha["id"]) for linha in ids]

            for item_id in ids_numericos:
                conexao.execute(
                    """
                    UPDATE fila_publicacao
                    SET
                        status = 'descartado',
                        atualizado_em = ?,
                        motivo_saida = 'Fila atingiu o limite; item de menor prioridade saiu.'
                    WHERE id = ?
                    """,
                    (agora_iso, item_id),
                )

        return len(ids_numericos)

    def obter_pendente_por_id(
        self,
        item_id: int,
    ) -> ItemFilaPublicacao | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT *
                FROM fila_publicacao
                WHERE id = ?
                  AND status = 'pendente'
                LIMIT 1
                """,
                (item_id,),
            ).fetchone()

        if linha is None:
            return None

        return self._converter_linha(linha)

    def segurar_item(
        self,
        item_id: int,
        minutos: int,
    ) -> bool:
        if minutos <= 0 or minutos > 10080:
            raise ValueError("Minutos de retencao precisam estar entre 1 e 10080.")

        agora = datetime.now().astimezone()
        segurado_ate = agora + timedelta(minutes=minutos)

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    segurado_ate = ?,
                    atualizado_em = ?
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (
                    segurado_ate.isoformat(timespec="seconds"),
                    agora.isoformat(timespec="seconds"),
                    item_id,
                ),
            )

        return cursor.rowcount > 0

    def agendar_item(
        self,
        item_id: int,
        para: datetime,
    ) -> bool:
        if para.tzinfo is None or para.utcoffset() is None:
            raise ValueError("Horario de agendamento precisa incluir fuso horario.")

        agora = datetime.now().astimezone()
        para_local = para.astimezone()

        if para_local <= agora:
            raise ValueError("Horario de agendamento precisa estar no futuro.")

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    agendado_para = ?,
                    segurado_ate = NULL,
                    atualizado_em = ?
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (
                    para_local.isoformat(timespec="seconds"),
                    agora.isoformat(timespec="seconds"),
                    item_id,
                ),
            )

        return cursor.rowcount > 0

    def liberar_item(
        self,
        item_id: int,
    ) -> bool:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    segurado_ate = NULL,
                    agendado_para = NULL,
                    atualizado_em = ?
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (agora, item_id),
            )

        return cursor.rowcount > 0

    def aprovar_item(
        self,
        item_id: int,
    ) -> bool:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    aprovado_manualmente = 1,
                    atualizado_em = ?
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (agora, item_id),
            )

        return cursor.rowcount > 0

    def revisar_item(
        self,
        item_id: int,
    ) -> bool:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    aprovado_manualmente = 0,
                    atualizado_em = ?
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (agora, item_id),
            )

        return cursor.rowcount > 0

    def obter_agendado_liberado(
        self,
        agora: datetime | None = None,
    ) -> ItemFilaPublicacao | None:
        referencia = agora or datetime.now().astimezone()

        if referencia.tzinfo is None or referencia.utcoffset() is None:
            referencia = referencia.astimezone()

        with self._conectar() as conexao:
            linhas = conexao.execute("""
                SELECT *
                FROM fila_publicacao
                WHERE status = 'pendente'
                  AND agendado_para IS NOT NULL
                ORDER BY agendado_para ASC, prioridade DESC, criado_em ASC
                """).fetchall()

        for linha in linhas:
            agendado_para = datetime.fromisoformat(linha["agendado_para"])
            segurado_ate = (
                datetime.fromisoformat(linha["segurado_ate"]) if linha["segurado_ate"] else None
            )

            if agendado_para > referencia:
                continue

            if segurado_ate is not None and segurado_ate > referencia:
                continue

            return self._converter_linha(linha)

        return None

    def adiantar_item(
        self,
        item_id: int,
    ) -> bool:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            existe = conexao.execute(
                """
                SELECT id
                FROM fila_publicacao
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (item_id,),
            ).fetchone()

            if existe is None:
                return False

            linha = conexao.execute("""
                SELECT MAX(prioridade) AS prioridade
                FROM fila_publicacao
                WHERE status = 'pendente'
                """).fetchone()

            prioridade_maxima = float(linha["prioridade"] or 0.0)

            conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    prioridade = ?,
                    atualizado_em = ?
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (
                    prioridade_maxima + 1.0,
                    agora,
                    item_id,
                ),
            )

        return True

    def adiar_item(
        self,
        item_id: int,
    ) -> bool:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            existe = conexao.execute(
                """
                SELECT id
                FROM fila_publicacao
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (item_id,),
            ).fetchone()

            if existe is None:
                return False

            linha = conexao.execute("""
                SELECT MIN(prioridade) AS prioridade
                FROM fila_publicacao
                WHERE status = 'pendente'
                """).fetchone()

            prioridade_minima = float(linha["prioridade"] or 0.0)

            conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    prioridade = ?,
                    atualizado_em = ?
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (
                    prioridade_minima - 1.0,
                    agora,
                    item_id,
                ),
            )

        return True

    def descartar_administrativamente(
        self,
        item_id: int,
    ) -> bool:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            cursor = conexao.execute(
                """
                UPDATE fila_publicacao
                SET
                    status = 'descartado',
                    atualizado_em = ?,
                    segurado_ate = NULL,
                    agendado_para = NULL,
                    aprovado_manualmente = 0,
                    motivo_saida = ?
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (
                    agora,
                    "Descartado por acao administrativa.",
                    item_id,
                ),
            )

        return cursor.rowcount > 0

    def solicitar_publicacao_imediata(
        self,
        item_id: int,
    ) -> bool:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")

        with self._conectar() as conexao:
            existe = conexao.execute(
                """
                SELECT id
                FROM fila_publicacao
                WHERE id = ?
                  AND status = 'pendente'
                """,
                (item_id,),
            ).fetchone()

            if existe is None:
                return False

            conexao.execute(
                """
                INSERT INTO controle_publicacao (
                    chave,
                    valor,
                    atualizado_em
                )
                VALUES (
                    'publicar_agora',
                    ?,
                    ?
                )
                ON CONFLICT(chave) DO UPDATE SET
                    valor = excluded.valor,
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    str(item_id),
                    agora,
                ),
            )

        return True

    def consumir_publicacao_imediata(
        self,
    ) -> ItemFilaPublicacao | None:
        with self._conectar() as conexao:
            registro = conexao.execute("""
                SELECT valor
                FROM controle_publicacao
                WHERE chave = 'publicar_agora'
                LIMIT 1
                """).fetchone()

            if registro is None:
                return None

            try:
                item_id = int(registro["valor"])
            except (TypeError, ValueError):
                conexao.execute("""
                    DELETE FROM controle_publicacao
                    WHERE chave = 'publicar_agora'
                    """)
                return None

            linha = conexao.execute(
                """
                SELECT *
                FROM fila_publicacao
                WHERE id = ?
                  AND status = 'pendente'
                LIMIT 1
                """,
                (item_id,),
            ).fetchone()

            conexao.execute("""
                DELETE FROM controle_publicacao
                WHERE chave = 'publicar_agora'
                """)

        if linha is None:
            return None

        return self._converter_linha(linha)

    def obter_ultima_publicacao_link(self, link: str) -> datetime | None:
        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT publicado_em
                FROM historico_publicacoes_fila
                WHERE link = ?
                ORDER BY publicado_em DESC
                LIMIT 1
                """,
                (link,),
            ).fetchone()

        if linha is None or not linha["publicado_em"]:
            return None

        try:
            return datetime.fromisoformat(str(linha["publicado_em"]))
        except ValueError:
            return None

    def historico_publicacoes_recentes(
        self,
        minutos: float,
        limite: int = 50,
    ) -> list[dict[str, Any]]:
        desde = datetime.now().astimezone() - timedelta(minutes=minutos)
        desde_iso = desde.isoformat(timespec="seconds")

        with self._conectar() as conexao:
            linhas = conexao.execute(
                """
                SELECT
                    chave_canonica,
                    chave_familia,
                    familia,
                    categoria,
                    marca,
                    tipo_oportunidade,
                    publicado_em,
                    pontuacao,
                    oferta_json
                FROM historico_publicacoes_fila
                WHERE publicado_em >= ?
                ORDER BY publicado_em DESC, id DESC
                LIMIT ?
                """,
                (desde_iso, limite),
            ).fetchall()

        historico: list[dict[str, Any]] = []

        for linha in linhas:
            registro = dict(linha)

            try:
                oferta = Oferta(**json.loads(registro["oferta_json"]))
                registro["preco"] = float(oferta.preco)
                registro["marketplace"] = getattr(
                    oferta,
                    "marketplace",
                    None,
                )
                registro["loja"] = getattr(
                    oferta,
                    "loja",
                    None,
                )
            except Exception:
                registro["preco"] = None
                registro["marketplace"] = None
                registro["loja"] = None

            registro.pop("oferta_json", None)
            historico.append(registro)

        return historico

    @staticmethod
    def _converter_linha(linha: sqlite3.Row) -> ItemFilaPublicacao:
        oferta = Oferta(**json.loads(linha["oferta_json"]))

        historico_dados = json.loads(linha["historico_json"]) if linha["historico_json"] else None

        resultado_historico = (
            ResultadoHistoricoPreco(**historico_dados) if historico_dados is not None else None
        )

        segurado_ate = (
            datetime.fromisoformat(linha["segurado_ate"]) if linha["segurado_ate"] else None
        )
        agendado_para = (
            datetime.fromisoformat(linha["agendado_para"]) if linha["agendado_para"] else None
        )

        return ItemFilaPublicacao(
            id=int(linha["id"]),
            oferta=oferta,
            resultado_historico=resultado_historico,
            pontuacao=float(linha["pontuacao"]),
            deve_republicar_por_queda=bool(linha["deve_republicar_por_queda"]),
            prioridade=float(linha["prioridade"]),
            segurado_ate=segurado_ate,
            agendado_para=agendado_para,
            aprovado_manualmente=bool(linha["aprovado_manualmente"]),
            criado_em=datetime.fromisoformat(linha["criado_em"]),
            atualizado_em=datetime.fromisoformat(linha["atualizado_em"]),
            status=str(linha["status"]),
        )
