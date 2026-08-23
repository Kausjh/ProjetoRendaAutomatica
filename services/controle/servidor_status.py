from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from services.controle.controlador import ControladorAdministrativo


class ServidorStatusAdministrativo:
    def __init__(
        self,
        controlador: ControladorAdministrativo,
        host: str = "127.0.0.1",
        porta: int = 8765,
    ) -> None:
        self.controlador = controlador
        self.host = host
        self.porta = porta
        self._servidor: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        if self._servidor is not None:
            return

        controlador = self.controlador

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path != "/status":
                    self._responder_json(
                        404,
                        {"erro": "Rota nao encontrada."},
                    )
                    return

                estado = controlador.obter_estado().como_dict()
                self._responder_json(200, estado)

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
