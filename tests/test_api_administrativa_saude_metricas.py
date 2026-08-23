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

TOKEN_TESTE = "token-administrativo-de-teste"


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


def criar_controlador(tmp_path):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    controlador = ControladorAdministrativo(
        orquestrador=OrquestradorFake(),
        fila=fila,
        verificador_chrome=lambda: True,
    )

    return fila, controlador


def criar_servidor(controlador):
    return ServidorStatusAdministrativo(
        controlador=controlador,
        host="127.0.0.1",
        porta=0,
        token=TOKEN_TESTE,
    )


def requisitar_json(url: str) -> tuple[int, dict]:
    requisicao = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {TOKEN_TESTE}"},
    )

    with urllib.request.urlopen(
        requisicao,
        timeout=2,
    ) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))
        return resposta.status, dados


def test_saude_retrata_componentes(tmp_path):
    _, controlador = criar_controlador(tmp_path)

    saude = controlador.obter_saude()

    assert saude["saudavel"] is True
    assert saude["componentes"]["runtime"] is True
    assert saude["componentes"]["publicador"] is True
    assert saude["componentes"]["bot"] is True
    assert saude["componentes"]["chrome_cdp"] is True


def test_saude_detecta_chrome_indisponivel(tmp_path):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    controlador = ControladorAdministrativo(
        orquestrador=OrquestradorFake(),
        fila=fila,
        verificador_chrome=lambda: False,
    )

    saude = controlador.obter_saude()

    assert saude["saudavel"] is False
    assert saude["componentes"]["chrome_cdp"] is False


def test_metricas_sem_publicacoes(tmp_path):
    _, controlador = criar_controlador(tmp_path)

    metricas = controlador.obter_metricas()

    assert metricas["publicacoes_24h"] == 0
    assert metricas["publicacoes_1h"] == 0
    assert metricas["fila_pendente"] == 0
    assert metricas["familias_pendentes"] == 0
    assert metricas["pontuacao_media_24h"] is None
    assert metricas["ultima_publicacao"] is None
    assert metricas["categorias_mais_publicadas"] == []


def test_endpoint_saude(tmp_path):
    _, controlador = criar_controlador(tmp_path)
    servidor = criar_servidor(controlador)

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status, dados = requisitar_json(f"http://127.0.0.1:{porta}/saude")

        assert status == 200
        assert dados["saudavel"] is True
        assert dados["componentes"]["chrome_cdp"] is True

    finally:
        servidor.encerrar()


def test_endpoint_metricas(tmp_path):
    _, controlador = criar_controlador(tmp_path)
    servidor = criar_servidor(controlador)

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status, dados = requisitar_json(f"http://127.0.0.1:{porta}/metricas")

        assert status == 200
        assert dados["publicacoes_24h"] == 0
        assert dados["fila_pendente"] == 0

    finally:
        servidor.encerrar()
