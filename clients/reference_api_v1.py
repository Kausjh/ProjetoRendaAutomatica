from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
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
        transporte_confiavel: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = (token or "").strip()
        self.timeout = float(timeout)
        self.transporte_confiavel = bool(transporte_confiavel)
        self._validar_politica_acesso()

    @staticmethod
    def _host_loopback(host: str) -> bool:
        if host.strip().lower() == "localhost":
            return True

        try:
            return ipaddress.ip_address(host).is_loopback
        except ValueError:
            return False

    def _validar_politica_acesso(self) -> None:
        parsed = urlsplit(self.base_url)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError("base_url deve usar http ou https.")

        if not parsed.hostname:
            raise ValueError("base_url precisa possuir host.")

        if parsed.username or parsed.password:
            raise ValueError("Credenciais na URL nao sao permitidas.")

        if parsed.query or parsed.fragment:
            raise ValueError("base_url nao pode conter query ou fragment.")

        if parsed.path not in {"", "/"}:
            raise ValueError("base_url deve apontar para a origem da API.")

        remoto = not self._host_loopback(parsed.hostname)

        if not remoto:
            return

        if not self.token:
            raise ValueError("Acesso remoto exige Bearer token.")

        if parsed.scheme == "http" and not self.transporte_confiavel:
            raise ValueError(
                "HTTP remoto exige transporte_confiavel=True " "e uma camada externa criptografada."
            )

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
