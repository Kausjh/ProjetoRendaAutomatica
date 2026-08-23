from __future__ import annotations

import json
import urllib.request

from repositories.fila_publicacao_repository import (
    FilaPublicacaoRepository,
)
from services.controle.controlador import ControladorAdministrativo
from services.controle.servidor_status import (
    ServidorStatusAdministrativo,
)


class ProcessoFake:
    def __init__(self, pid: int) -> None:
        self.pid = pid

    def poll(self) -> int | None:
        return None


class OrquestradorFake:
    def __init__(self) -> None:
        self._encerrando = False
        self.processo_pipeline = None
        self.processo_publicador = ProcessoFake(200)
        self.processo_bot = ProcessoFake(300)

    def internet_disponivel(self) -> bool:
        return True

    def telegram_disponivel(self) -> bool:
        return True

    def mercado_livre_disponivel(self) -> bool:
        return True


def test_servidor_status_responde_json(tmp_path):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    controlador = ControladorAdministrativo(
        orquestrador=OrquestradorFake(),
        fila=fila,
    )

    servidor = ServidorStatusAdministrativo(
        controlador=controlador,
        host="127.0.0.1",
        porta=0,
    )

    servidor.iniciar()

    try:
        porta_real = servidor._servidor.server_address[1]

        with urllib.request.urlopen(
            f"http://127.0.0.1:{porta_real}/status",
            timeout=2,
        ) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))

        assert resposta.status == 200
        assert dados["runtime_ativo"] is True
        assert dados["publicador"]["ativo"] is True
        assert dados["fila"]["pendentes"] == 0
        assert dados["conectividade"]["telegram"] is True

    finally:
        servidor.encerrar()
