# 63.8738, -149.7525

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RadarEditorialRepository:
    """Memória pequena e local da camada editorial do canal."""

    LIMITE_INTERVENCOES = 100
    DIAS_RETENCAO = 21

    def __init__(
        self,
        caminho_arquivo: str | Path = "database/radar_editorial.json",
    ) -> None:
        self.caminho_arquivo = Path(caminho_arquivo)
        self.caminho_arquivo.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _vazio() -> dict[str, Any]:
        return {
            "intervencoes": [],
            "interacoes_diarias": {},
        }

    def _carregar(self) -> dict[str, Any]:
        if not self.caminho_arquivo.exists():
            return self._vazio()

        try:
            dados = json.loads(self.caminho_arquivo.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning(
                "Memória do Radar Editorial não pôde ser lida; "
                "a execução seguirá sem histórico editorial."
            )
            return self._vazio()

        if not isinstance(dados, dict):
            return self._vazio()

        intervencoes = dados.get("intervencoes")
        interacoes = dados.get("interacoes_diarias")

        if not isinstance(intervencoes, list):
            intervencoes = []

        if not isinstance(interacoes, dict):
            interacoes = {}

        return {
            "intervencoes": intervencoes,
            "interacoes_diarias": interacoes,
        }

    def _salvar(self, dados: dict[str, Any]) -> None:
        self._podar(dados)

        temporario = self.caminho_arquivo.with_suffix(self.caminho_arquivo.suffix + ".tmp")
        temporario.write_text(
            json.dumps(
                dados,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        temporario.replace(self.caminho_arquivo)

    def _podar(self, dados: dict[str, Any]) -> None:
        intervencoes = dados.get("intervencoes", [])
        if isinstance(intervencoes, list):
            dados["intervencoes"] = intervencoes[-self.LIMITE_INTERVENCOES :]

        interacoes = dados.get("interacoes_diarias", {})
        if not isinstance(interacoes, dict):
            dados["interacoes_diarias"] = {}
            return

        limite = date.today() - timedelta(days=self.DIAS_RETENCAO)
        mantidas: dict[str, Any] = {}

        for chave, valor in interacoes.items():
            try:
                data_chave = date.fromisoformat(str(chave))
            except ValueError:
                continue

            if data_chave >= limite:
                mantidas[str(chave)] = valor

        dados["interacoes_diarias"] = mantidas

    def registrar_intervencao(
        self,
        *,
        persona: str,
        motivo: str,
        texto: str,
        momento: datetime,
    ) -> None:
        dados = self._carregar()
        intervencoes = dados["intervencoes"]

        intervencoes.append(
            {
                "persona": persona,
                "motivo": motivo,
                "texto": texto,
                "criado_em": momento.isoformat(timespec="seconds"),
            }
        )

        self._salvar(dados)

    def intervencoes_recentes(self, limite: int = 40) -> list[dict[str, Any]]:
        dados = self._carregar()
        intervencoes = dados["intervencoes"]

        return [item for item in intervencoes[-max(1, limite) :] if isinstance(item, dict)]

    def comentarios_no_dia(self, data_referencia: date) -> int:
        prefixo = data_referencia.isoformat()

        return sum(
            1
            for item in self.intervencoes_recentes(self.LIMITE_INTERVENCOES)
            if str(item.get("criado_em") or "").startswith(prefixo)
        )

    def ultima_intervencao_em(self) -> datetime | None:
        itens = self.intervencoes_recentes(1)
        if not itens:
            return None

        valor = itens[-1].get("criado_em")
        if not valor:
            return None

        try:
            return datetime.fromisoformat(str(valor))
        except ValueError:
            return None

    def ultima_persona(self) -> str | None:
        itens = self.intervencoes_recentes(1)
        if not itens:
            return None

        valor = itens[-1].get("persona")
        return str(valor) if valor else None

    def textos_recentes(self, limite: int = 40) -> list[str]:
        return [
            str(item.get("texto"))
            for item in self.intervencoes_recentes(limite)
            if item.get("texto")
        ]

    def interacao_diaria_enviada(self, data_referencia: date) -> bool:
        dados = self._carregar()
        interacoes = dados["interacoes_diarias"]
        registro = interacoes.get(data_referencia.isoformat())

        return isinstance(registro, dict) and bool(registro.get("enviada"))

    def registrar_interacao_diaria(
        self,
        *,
        data_referencia: date,
        tipo: str,
        momento: datetime,
    ) -> None:
        dados = self._carregar()
        interacoes = dados["interacoes_diarias"]
        interacoes[data_referencia.isoformat()] = {
            "enviada": True,
            "tipo": tipo,
            "enviada_em": momento.isoformat(timespec="seconds"),
        }
        self._salvar(dados)
