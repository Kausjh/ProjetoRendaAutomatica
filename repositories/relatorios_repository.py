import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RelatoriosRepository:
    def __init__(self, caminho_arquivo: str = "database/relatorios_execucao.json") -> None:
        self.caminho_arquivo = Path(caminho_arquivo)

        self.caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)

        if not self.caminho_arquivo.exists():
            self._salvar_relatorios([])

    def salvar(self, relatorio: dict[str, Any]) -> None:
        relatorios = self._carregar_relatorios()

        relatorios.append(relatorio)

        self._salvar_relatorios(relatorios)

        logger.info("Relatório da execução salvo em: %s", self.caminho_arquivo)

    def _carregar_relatorios(self) -> list[dict[str, Any]]:
        try:
            with self.caminho_arquivo.open(mode="r", encoding="utf-8") as arquivo:
                conteudo = json.load(arquivo)

        except (json.JSONDecodeError, OSError):
            logger.exception("Não foi possível ler o histórico de relatórios.")

            return []

        if not isinstance(conteudo, list):
            logger.warning(
                "O arquivo de relatórios possui formato inválido. "
                "Um novo histórico será iniciado."
            )

            return []

        return conteudo

    def _salvar_relatorios(self, relatorios: list[dict[str, Any]]) -> None:
        try:
            with self.caminho_arquivo.open(mode="w", encoding="utf-8") as arquivo:
                json.dump(relatorios, arquivo, ensure_ascii=False, indent=4)

        except OSError:
            logger.exception("Não foi possível salvar o histórico de relatórios.")
