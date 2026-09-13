from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class ErroApiAplicacao(RuntimeError):
    status: int | None
    mensagem: str

    def __str__(self) -> str:
        if self.status is None:
            return self.mensagem
        return f"HTTP {self.status}: {self.mensagem}"


class ClienteApiAplicacaoV1:
    """Cliente de referencia read-only para /api/v1."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8766",
        *,
        token: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = (token or "").strip()
        self.timeout = float(timeout)

    def health(self) -> dict[str, Any]:
        return self._get("/api/v1/health")

    def listar_produtos(
        self,
        *,
        limite: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self._get(
            "/api/v1/produtos",
            query={"limite": limite, "offset": offset},
        )

    def obter_produto(
        self,
        chave_canonica: str,
    ) -> dict[str, Any]:
        chave = quote(str(chave_canonica).strip(), safe="")
        return self._get(f"/api/v1/produtos/{chave}")

    def listar_historico(
        self,
        chave_canonica: str,
        *,
        limite: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        chave = quote(str(chave_canonica).strip(), safe="")
        return self._get(
            f"/api/v1/produtos/{chave}/historico",
            query={"limite": limite, "offset": offset},
        )

    def listar_alertas(
        self,
        *,
        limite: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        return self._get(
            "/api/v1/alertas",
            query={"limite": limite, "offset": offset},
        )

    def _get(
        self,
        path: str,
        *,
        query: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        url = self.base_url + path

        if query:
            url += "?" + urlencode({chave: str(valor) for chave, valor in query.items()})

        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        request = Request(url, method="GET", headers=headers)

        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as erro:
            mensagem = self._mensagem_erro(erro)
            raise ErroApiAplicacao(
                status=int(erro.code),
                mensagem=mensagem,
            ) from erro
        except URLError as erro:
            raise ErroApiAplicacao(
                status=None,
                mensagem=f"Falha de conexao: {erro.reason}",
            ) from erro

        dados = json.loads(payload)
        if not isinstance(dados, dict):
            raise ErroApiAplicacao(
                status=None,
                mensagem="Resposta JSON nao e um objeto.",
            )

        return dados

    @staticmethod
    def _mensagem_erro(erro: HTTPError) -> str:
        try:
            payload = json.loads(erro.read().decode("utf-8"))
        except Exception:
            return str(erro.reason)

        if isinstance(payload, dict):
            mensagem = payload.get("erro")
            if mensagem:
                return str(mensagem)

        return str(erro.reason)
