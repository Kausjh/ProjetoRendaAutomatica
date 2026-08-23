from __future__ import annotations

import json
import urllib.error
import urllib.request

from repositories.fila_publicacao_repository import (
    FilaPublicacaoRepository,
)
from services.controle.controlador import ControladorAdministrativo
from services.controle.servidor_status import (
    ServidorStatusAdministrativo,
)

TOKEN_TESTE = "token-administrativo-de-teste"


class OrquestradorFake:
    def __init__(self) -> None:
        self._encerrando = False
        self.processo_pipeline = None
        self.processo_publicador = None
        self.processo_bot = None

    def internet_disponivel(self) -> bool:
        return True

    def telegram_disponivel(self) -> bool:
        return True

    def mercado_livre_disponivel(self) -> bool:
        return True


def criar_servidor(tmp_path):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    controlador = ControladorAdministrativo(
        orquestrador=OrquestradorFake(),
        fila=fila,
        verificador_chrome=lambda: True,
    )

    servidor = ServidorStatusAdministrativo(
        controlador=controlador,
        host="127.0.0.1",
        porta=0,
        token=TOKEN_TESTE,
    )

    return servidor


def test_api_recusa_requisicao_sem_token(tmp_path):
    servidor = criar_servidor(tmp_path)
    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        requisicao = urllib.request.Request(f"http://127.0.0.1:{porta}/status")

        try:
            urllib.request.urlopen(
                requisicao,
                timeout=2,
            )
        except urllib.error.HTTPError as erro:
            dados = json.loads(erro.read().decode("utf-8"))

            assert erro.code == 401
            assert dados == {"erro": "Nao autorizado."}
        else:
            raise AssertionError("API aceitou requisicao sem token.")

    finally:
        servidor.encerrar()


def test_api_recusa_token_incorreto(tmp_path):
    servidor = criar_servidor(tmp_path)
    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        requisicao = urllib.request.Request(
            f"http://127.0.0.1:{porta}/status",
            headers={"Authorization": "Bearer token-incorreto"},
        )

        try:
            urllib.request.urlopen(
                requisicao,
                timeout=2,
            )
        except urllib.error.HTTPError as erro:
            assert erro.code == 401
        else:
            raise AssertionError("API aceitou token incorreto.")

    finally:
        servidor.encerrar()


def test_api_aceita_token_correto(tmp_path):
    servidor = criar_servidor(tmp_path)
    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        requisicao = urllib.request.Request(
            f"http://127.0.0.1:{porta}/status",
            headers={"Authorization": (f"Bearer {TOKEN_TESTE}")},
        )

        with urllib.request.urlopen(
            requisicao,
            timeout=2,
        ) as resposta:
            dados = json.loads(resposta.read().decode("utf-8"))

        assert resposta.status == 200
        assert "runtime_ativo" in dados

    finally:
        servidor.encerrar()


def test_servidor_sem_token_preserva_modo_local(tmp_path):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    controlador = ControladorAdministrativo(
        orquestrador=OrquestradorFake(),
        fila=fila,
        verificador_chrome=lambda: True,
    )

    servidor = ServidorStatusAdministrativo(
        controlador=controlador,
        host="127.0.0.1",
        porta=0,
        token="",
    )

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        with urllib.request.urlopen(
            f"http://127.0.0.1:{porta}/status",
            timeout=2,
        ) as resposta:
            assert resposta.status == 200

    finally:
        servidor.encerrar()
