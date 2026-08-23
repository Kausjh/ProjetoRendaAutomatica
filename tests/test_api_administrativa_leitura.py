from __future__ import annotations

import json
import urllib.request

from models.oferta import Oferta
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


def criar_oferta() -> Oferta:
    return Oferta(
        nome="Produto de teste",
        loja="Mercado Livre",
        preco=100.0,
        preco_antigo=150.0,
        link="https://example.com/produto",
        imagem=None,
    )


def criar_servidor(tmp_path):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))

    controle = ControladorAdministrativo(
        orquestrador=OrquestradorFake(),
        fila=fila,
    )

    servidor = ServidorStatusAdministrativo(
        controlador=controle,
        host="127.0.0.1",
        porta=0,
        token=TOKEN_TESTE,
    )

    return fila, servidor


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


def test_endpoint_fila_lista_pendentes(tmp_path):
    fila, servidor = criar_servidor(tmp_path)

    fila.adicionar_ou_atualizar(
        oferta=criar_oferta(),
        resultado_historico=None,
        pontuacao=87.5,
        deve_republicar_por_queda=False,
        prioridade=90.0,
    )

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status, dados = requisitar_json(f"http://127.0.0.1:{porta}/fila")

        assert status == 200
        assert dados["quantidade"] == 1
        assert dados["itens"][0]["nome"] == "Produto de teste"
        assert dados["itens"][0]["pontuacao"] == 87.5
        assert dados["itens"][0]["prioridade"] == 90.0

    finally:
        servidor.encerrar()


def test_endpoint_publicacoes_responde_lista(tmp_path):
    _, servidor = criar_servidor(tmp_path)

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status, dados = requisitar_json(f"http://127.0.0.1:{porta}/publicacoes")

        assert status == 200
        assert dados["quantidade"] == 0
        assert dados["periodo_minutos"] == 1440.0
        assert dados["itens"] == []

    finally:
        servidor.encerrar()


def test_endpoint_aceita_parametros(tmp_path):
    _, servidor = criar_servidor(tmp_path)

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status, dados = requisitar_json(
            f"http://127.0.0.1:{porta}/publicacoes" "?limite=10&minutos=60"
        )

        assert status == 200
        assert dados["periodo_minutos"] == 60.0

    finally:
        servidor.encerrar()
