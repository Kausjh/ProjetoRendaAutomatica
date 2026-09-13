from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from models.oferta import Oferta
from repositories.catalogo_canonico_repository import (
    CatalogoCanonicoRepository,
)
from services.catalogo_canonico_service import (
    CatalogoCanonicoService,
)


class BootstrapCatalogoCanonicoService:
    FONTES = (
        ("fila_publicacao", "fila_publicacao"),
        (
            "historico_publicacoes_fila",
            "historico_publicacoes_fila",
        ),
    )

    def __init__(
        self,
        *,
        caminho_fila: str | Path = "database/fila_publicacao.sqlite3",
        caminho_catalogo: str | Path = "database/catalogo_canonico.sqlite3",
        confianca_minima: float = 90.0,
    ) -> None:
        self.caminho_fila = Path(caminho_fila)
        self.caminho_catalogo = Path(caminho_catalogo)
        self.confianca_minima = float(confianca_minima)

        if not 0 <= self.confianca_minima <= 100:
            raise ValueError("confianca_minima precisa estar entre 0 e 100.")

    def simular(self) -> dict[str, object]:
        if not self.caminho_fila.exists():
            raise FileNotFoundError(f"Banco da fila nao encontrado: {self.caminho_fila}")

        with TemporaryDirectory() as diretorio:
            caminho_simulado = Path(diretorio) / "catalogo_canonico_simulado.sqlite3"

            self._copiar_catalogo_para_simulacao(caminho_simulado)

            repository = CatalogoCanonicoRepository(caminho_simulado)
            resultado = self._processar(
                repository=repository,
                modo="simulacao",
            )

        return resultado

    def executar(self) -> dict[str, object]:
        if not self.caminho_fila.exists():
            raise FileNotFoundError(f"Banco da fila nao encontrado: {self.caminho_fila}")

        repository = CatalogoCanonicoRepository(self.caminho_catalogo)

        return self._processar(
            repository=repository,
            modo="execucao",
        )

    def _processar(
        self,
        *,
        repository: CatalogoCanonicoRepository,
        modo: str,
    ) -> dict[str, object]:
        catalogo_service = CatalogoCanonicoService(
            repository=repository,
            confianca_minima=self.confianca_minima,
        )

        antes = repository.obter_metricas()

        totais: Counter[str] = Counter()
        por_fonte: dict[str, dict[str, int]] = {}

        with self._conectar_fila_read_only() as conexao:
            tabelas = {str(linha["name"]) for linha in conexao.execute("""
                    SELECT name
                    FROM sqlite_master
                    WHERE type = 'table'
                    """).fetchall()}

            for fonte, tabela in self.FONTES:
                stats = Counter()
                por_fonte[fonte] = stats

                if tabela not in tabelas:
                    stats["tabela_ausente"] += 1
                    totais["tabela_ausente"] += 1
                    continue

                linhas = conexao.execute(f"""
                    SELECT id, oferta_json
                    FROM {tabela}
                    WHERE oferta_json IS NOT NULL
                    ORDER BY id ASC
                    """).fetchall()

                for linha in linhas:
                    self._processar_linha(
                        repository=repository,
                        catalogo_service=catalogo_service,
                        stats=stats,
                        totais=totais,
                        oferta_json=linha["oferta_json"],
                    )

        depois = repository.obter_metricas()

        return {
            "modo": modo,
            "confianca_minima": self.confianca_minima,
            "fontes": {fonte: dict(sorted(stats.items())) for fonte, stats in por_fonte.items()},
            "totais": dict(sorted(totais.items())),
            "catalogo_antes": antes,
            "catalogo_depois": depois,
        }

    def _processar_linha(
        self,
        *,
        repository: CatalogoCanonicoRepository,
        catalogo_service: CatalogoCanonicoService,
        stats: Counter[str],
        totais: Counter[str],
        oferta_json: str,
    ) -> None:
        self._incrementar(
            stats,
            totais,
            "registros_lidos",
        )

        try:
            payload = json.loads(oferta_json)
        except Exception:
            self._incrementar(
                stats,
                totais,
                "json_invalidos",
            )
            return

        if not isinstance(
            payload,
            dict,
        ):
            self._incrementar(
                stats,
                totais,
                "json_nao_objeto",
            )
            return

        try:
            oferta = Oferta(**payload)
        except (TypeError, ValueError):
            self._incrementar(
                stats,
                totais,
                "oferta_incompativel",
            )
            return

        chave = self._texto(oferta.chave_produto_canonica)
        produto = self._texto(oferta.produto_canonico)
        marketplace_bruto = self._texto(oferta.marketplace or oferta.loja)
        identificador = self._texto(oferta.id_anuncio or oferta.id_produto)

        try:
            confianca = float(oferta.confianca_normalizacao or 0.0)
        except (TypeError, ValueError):
            confianca = 0.0

        if not (chave and produto and marketplace_bruto and identificador):
            self._incrementar(
                stats,
                totais,
                "incompletos",
            )
            return

        if confianca < self.confianca_minima:
            self._incrementar(
                stats,
                totais,
                "baixa_confianca",
            )
            return

        marketplace = catalogo_service._normalizar_marketplace(marketplace_bruto)

        if not marketplace:
            self._incrementar(
                stats,
                totais,
                "marketplace_invalido",
            )
            return

        self._incrementar(
            stats,
            totais,
            "elegiveis",
        )

        existente = repository.obter_por_anuncio(
            marketplace=marketplace,
            identificador=identificador,
        )

        if existente is not None:
            if existente.chave_canonica == chave:
                self._incrementar(
                    stats,
                    totais,
                    "ja_presentes",
                )
                return

            self._incrementar(
                stats,
                totais,
                "conflitos_detectados",
            )

            if repository.existe_conflito(
                marketplace=marketplace,
                identificador=identificador,
                chave_existente=existente.chave_canonica,
                chave_observada=chave,
            ):
                self._incrementar(
                    stats,
                    totais,
                    "conflitos_ja_registrados",
                )
                return

            resultado = catalogo_service.observar(oferta)

            if resultado.status != "conflito_anuncio":
                raise RuntimeError(
                    "Conflito esperado nao foi preservado " f"para {marketplace}:{identificador}."
                )

            self._incrementar(
                stats,
                totais,
                "conflitos_registrados",
            )
            return

        resultado = catalogo_service.observar(oferta)

        if not resultado.registrado:
            self._incrementar(
                stats,
                totais,
                f"ignorado_{resultado.status}",
            )
            return

        self._incrementar(
            stats,
            totais,
            resultado.status,
        )
        self._incrementar(
            stats,
            totais,
            "registrados",
        )

    def _copiar_catalogo_para_simulacao(
        self,
        destino: Path,
    ) -> None:
        if not self.caminho_catalogo.exists():
            return

        origem_uri = "file:" + self.caminho_catalogo.resolve().as_posix() + "?mode=ro"

        origem = sqlite3.connect(
            origem_uri,
            uri=True,
        )
        destino_conexao = sqlite3.connect(destino)

        try:
            origem.backup(destino_conexao)
        finally:
            destino_conexao.close()
            origem.close()

    def _conectar_fila_read_only(
        self,
    ) -> sqlite3.Connection:
        uri = "file:" + self.caminho_fila.resolve().as_posix() + "?mode=ro"
        conexao = sqlite3.connect(
            uri,
            uri=True,
        )
        conexao.row_factory = sqlite3.Row
        return conexao

    @staticmethod
    def _texto(
        valor,
    ) -> str | None:
        texto = str(valor or "").strip()

        return texto or None

    @staticmethod
    def _incrementar(
        stats: Counter[str],
        totais: Counter[str],
        chave: str,
    ) -> None:
        stats[chave] += 1
        totais[chave] += 1
