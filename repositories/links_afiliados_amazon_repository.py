# 63.8738, -149.7525

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, urlparse


class LinksAfiliadosAmazonRepository:
    """Mapeia p?ginas Amazon para links oficiais gerados pelo SiteStripe."""

    PADROES_ASIN = (
        re.compile(
            r"/dp/([A-Z0-9]{10})(?:[/?]|$)",
            re.IGNORECASE,
        ),
        re.compile(
            r"/gp/product/([A-Z0-9]{10})(?:[/?]|$)",
            re.IGNORECASE,
        ),
        re.compile(
            r"/gp/aw/d/([A-Z0-9]{10})(?:[/?]|$)",
            re.IGNORECASE,
        ),
    )

    def __init__(
        self,
        caminho_arquivo: str | Path = ("database/links_afiliados_amazon.sqlite3"),
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

        conexao.execute("PRAGMA journal_mode=WAL")

        conexao.execute("PRAGMA synchronous=NORMAL")

        return conexao

    def _criar_estrutura(
        self,
    ) -> None:
        with self._conectar() as conexao:
            conexao.execute("""
                CREATE TABLE IF NOT EXISTS links_amazon (
                    chave TEXT PRIMARY KEY,
                    link_original TEXT NOT NULL,
                    link_afiliado TEXT NOT NULL,
                    criado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    atualizado_em TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """)

    def registrar(
        self,
        link_original: str,
        link_afiliado: str,
    ) -> None:
        chave = self.criar_chave(link_original)

        if not self.link_afiliado_valido(link_afiliado):
            raise ValueError("O link afiliado Amazon precisa " "ser um link oficial do SiteStripe.")

        with self._conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO links_amazon (
                    chave,
                    link_original,
                    link_afiliado
                )
                VALUES (?, ?, ?)
                ON CONFLICT(chave) DO UPDATE SET
                    link_original = excluded.link_original,
                    link_afiliado = excluded.link_afiliado,
                    atualizado_em = CURRENT_TIMESTAMP
                """,
                (
                    chave,
                    link_original.strip(),
                    link_afiliado.strip(),
                ),
            )

    def obter_link_afiliado(
        self,
        link_original: str,
    ) -> str | None:
        chave = self.criar_chave(link_original)

        with self._conectar() as conexao:
            linha = conexao.execute(
                """
                SELECT link_afiliado
                FROM links_amazon
                WHERE chave = ?
                """,
                (chave,),
            ).fetchone()

        if linha is None:
            return None

        link = str(linha[0]).strip()

        if not self.link_afiliado_valido(link):
            return None

        return link

    @classmethod
    def criar_chave(
        cls,
        link: str,
    ) -> str:
        parsed = urlparse(str(link).strip())

        host = cls._normalizar_host(parsed.hostname)

        if not cls._eh_amazon(host):
            raise ValueError("O link original nao pertence " "a amazon.com.br.")

        caminho = parsed.path or "/"

        for padrao in cls.PADROES_ASIN:
            correspondencia = padrao.search(caminho)

            if correspondencia:
                return "asin:" + correspondencia.group(1).upper()

        caminho = re.sub(
            r"/+",
            "/",
            caminho,
        )

        if caminho != "/":
            caminho = caminho.rstrip("/")

        return "url:amazon.com.br" + caminho

    @classmethod
    def link_afiliado_valido(
        cls,
        link: str,
    ) -> bool:
        if not isinstance(
            link,
            str,
        ):
            return False

        parsed = urlparse(link.strip())

        if parsed.scheme != "https":
            return False

        host = cls._normalizar_host(parsed.hostname)

        # Encurtador oficial usado pelo SiteStripe.
        if host == "amzn.to":
            return bool(parsed.path.strip("/"))

        if not cls._eh_amazon(host):
            return False

        parametros = parse_qs(parsed.query)

        # Links longos do SiteStripe carregam a tag
        # de associado/rastreamento.
        return bool(parametros.get("tag"))

    @staticmethod
    def _normalizar_host(
        host: str | None,
    ) -> str:
        valor = str(host or "").strip().lower()

        if valor.startswith("www."):
            valor = valor[4:]

        return valor

    @staticmethod
    def _eh_amazon(
        host: str,
    ) -> bool:
        return host == "amazon.com.br" or host.endswith(".amazon.com.br")
