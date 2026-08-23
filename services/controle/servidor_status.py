from __future__ import annotations

import hmac
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv

from services.controle.controlador import ControladorAdministrativo


class ServidorStatusAdministrativo:
    def __init__(
        self,
        controlador: ControladorAdministrativo,
        host: str = "127.0.0.1",
        porta: int = 8765,
        token: str | None = None,
    ) -> None:
        self.controlador = controlador

        load_dotenv()

        token_ambiente = os.getenv("RADAR_ADMIN_TOKEN", "").strip()
        self.token = token.strip() if token is not None else token_ambiente
        self.host = host
        self.porta = porta
        self._servidor: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        if self._servidor is not None:
            return

        controlador = self.controlador
        token_administrativo = self.token

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if token_administrativo:
                    autorizacao = self.headers.get(
                        "Authorization",
                        "",
                    )

                    prefixo = "Bearer "
                    token_recebido = (
                        autorizacao[len(prefixo) :].strip()
                        if autorizacao.startswith(prefixo)
                        else ""
                    )

                    autorizado = bool(token_recebido) and hmac.compare_digest(
                        token_recebido,
                        token_administrativo,
                    )

                    if not autorizado:
                        self._responder_json(
                            401,
                            {"erro": "Nao autorizado."},
                        )
                        return

                url = urlparse(self.path)
                rota = url.path
                parametros = parse_qs(url.query)

                try:
                    if rota == "/status":
                        dados = controlador.obter_estado().como_dict()
                        self._responder_json(200, dados)
                        return

                    if rota == "/saude":
                        dados = controlador.obter_saude()
                        self._responder_json(200, dados)
                        return

                    if rota == "/metricas":
                        dados = controlador.obter_metricas()
                        self._responder_json(200, dados)
                        return

                    if rota == "/fila":
                        limite = self._obter_inteiro(
                            parametros,
                            "limite",
                            50,
                        )

                        dados = controlador.listar_fila(
                            limite=limite,
                        )
                        self._responder_json(200, dados)
                        return

                    if rota == "/publicacoes":
                        limite = self._obter_inteiro(
                            parametros,
                            "limite",
                            50,
                        )
                        minutos = self._obter_decimal(
                            parametros,
                            "minutos",
                            1440.0,
                        )

                        dados = controlador.listar_publicacoes(
                            minutos=minutos,
                            limite=limite,
                        )
                        self._responder_json(200, dados)
                        return

                except ValueError as erro:
                    self._responder_json(
                        400,
                        {"erro": str(erro)},
                    )
                    return

                self._responder_json(
                    404,
                    {"erro": "Rota nao encontrada."},
                )

            @staticmethod
            def _obter_inteiro(
                parametros: dict[str, list[str]],
                nome: str,
                padrao: int,
            ) -> int:
                valores = parametros.get(nome)

                if not valores:
                    return padrao

                try:
                    return int(valores[0])
                except ValueError as erro:
                    raise ValueError(f"Parametro '{nome}' precisa ser inteiro.") from erro

            @staticmethod
            def _obter_decimal(
                parametros: dict[str, list[str]],
                nome: str,
                padrao: float,
            ) -> float:
                valores = parametros.get(nome)

                if not valores:
                    return padrao

                try:
                    return float(valores[0])
                except ValueError as erro:
                    raise ValueError(f"Parametro '{nome}' precisa ser numerico.") from erro

            def _responder_json(
                self,
                status: int,
                dados: dict[str, Any],
            ) -> None:
                corpo = json.dumps(
                    dados,
                    ensure_ascii=False,
                    indent=2,
                ).encode("utf-8")

                self.send_response(status)
                self.send_header(
                    "Content-Type",
                    "application/json; charset=utf-8",
                )
                self.send_header(
                    "Content-Length",
                    str(len(corpo)),
                )
                self.end_headers()
                self.wfile.write(corpo)

            def log_message(
                self,
                format: str,
                *args: object,
            ) -> None:
                return

        self._servidor = ThreadingHTTPServer(
            (self.host, self.porta),
            Handler,
        )

        self._thread = threading.Thread(
            target=self._servidor.serve_forever,
            name="servidor-status-administrativo",
            daemon=True,
        )
        self._thread.start()

    def encerrar(self) -> None:
        servidor = self._servidor

        if servidor is None:
            return

        servidor.shutdown()
        servidor.server_close()

        thread = self._thread

        if thread is not None:
            thread.join(timeout=5)

        self._servidor = None
        self._thread = None
