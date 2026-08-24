from __future__ import annotations

import json
import urllib.error
import urllib.request

from models.oferta import Oferta
from repositories.controle_administrativo_repository import (
    ControleAdministrativoRepository,
)
from repositories.fila_publicacao_repository import FilaPublicacaoRepository
from services.controle.controlador import ControladorAdministrativo
from services.controle.servidor_status import ServidorStatusAdministrativo

TOKEN_TESTE = "token-administrativo-de-teste"


class OrquestradorFake:
    def __init__(self) -> None:
        self._encerrando = False
        self.processo_pipeline = None
        self.processo_publicador = None
        self.processo_bot = None
        self.publicador_pausado = False
        self.pipeline_imediato_pendente = False
        self.reinicio_chrome_em_andamento = False

    def internet_disponivel(self) -> bool:
        return True

    def telegram_disponivel(self) -> bool:
        return True

    def mercado_livre_disponivel(self) -> bool:
        return True

    def pausar_publicador(self) -> str:
        self.publicador_pausado = True
        return "pausado"

    def retomar_publicador(self) -> str:
        self.publicador_pausado = False
        return "retomado"

    def solicitar_pipeline_imediato(self) -> str:
        self.pipeline_imediato_pendente = True
        return "solicitado"

    def reiniciar_bot_administrativamente(self) -> str:
        return "reiniciado"

    def solicitar_reinicio_chrome(self) -> str:
        self.reinicio_chrome_em_andamento = True
        return "solicitado"


def criar_oferta() -> Oferta:
    return Oferta(
        nome="Produto administrativo",
        loja="Mercado Livre",
        preco=100.0,
        preco_antigo=150.0,
        link="https://example.com/admin",
        imagem=None,
    )


def criar_servidor(tmp_path):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))
    admin = ControleAdministrativoRepository(str(tmp_path / "controle.sqlite3"))
    orquestrador = OrquestradorFake()

    controlador = ControladorAdministrativo(
        orquestrador=orquestrador,
        fila=fila,
        verificador_chrome=lambda: True,
        repositorio_admin=admin,
    )

    servidor = ServidorStatusAdministrativo(
        controlador=controlador,
        host="127.0.0.1",
        porta=0,
        token=TOKEN_TESTE,
    )

    return fila, admin, orquestrador, servidor


def requisitar(
    url: str,
    metodo: str = "GET",
    token: str | None = TOKEN_TESTE,
) -> tuple[int, dict]:
    headers = {
        "X-Radar-Device": "pytest-android",
    }

    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    requisicao = urllib.request.Request(
        url,
        headers=headers,
        method=metodo,
    )

    with urllib.request.urlopen(
        requisicao,
        timeout=2,
    ) as resposta:
        dados = json.loads(resposta.read().decode("utf-8"))

        return resposta.status, dados


def test_post_fila_adiantar_e_audita(tmp_path):
    fila, admin, _, servidor = criar_servidor(tmp_path)

    fila.adicionar_ou_atualizar(
        oferta=criar_oferta(),
        resultado_historico=None,
        pontuacao=90.0,
        deve_republicar_por_queda=False,
        prioridade=80.0,
    )

    item_id = fila.listar_pendentes(limite=1)[0].id

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status, dados = requisitar(
            (f"http://127.0.0.1:{porta}" f"/fila/{item_id}/adiantar"),
            metodo="POST",
        )

        assert status == 200
        assert dados["sucesso"] is True
        assert dados["acao"] == "adiantar"

        auditoria = admin.listar_auditoria(limite=10)

        assert auditoria[0]["acao"] == "fila.adiantar"
        assert auditoria[0]["alvo"] == str(item_id)
        assert auditoria[0]["dispositivo"] == "pytest-android"
        assert auditoria[0]["resultado"] == "sucesso"

    finally:
        servidor.encerrar()


def test_post_operacao_pausa_publicador(tmp_path):
    _, admin, orquestrador, servidor = criar_servidor(tmp_path)

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status, dados = requisitar(
            (f"http://127.0.0.1:{porta}" "/operacao/publicador/pausar"),
            metodo="POST",
        )

        assert status == 200
        assert dados["resultado"] == "pausado"
        assert orquestrador.publicador_pausado is True
        assert dados["operacao"]["publicador_pausado"] is True

        auditoria = admin.listar_auditoria(limite=10)

        assert auditoria[0]["acao"] == "operacao.publicador.pausar"

    finally:
        servidor.encerrar()


def test_get_operacao_e_auditoria(tmp_path):
    _, _, _, servidor = criar_servidor(tmp_path)

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status_operacao, operacao = requisitar(f"http://127.0.0.1:{porta}/operacao")

        status_auditoria, auditoria = requisitar(f"http://127.0.0.1:{porta}/auditoria")

        assert status_operacao == 200
        assert operacao["publicador_pausado"] is False
        assert status_auditoria == 200
        assert auditoria["quantidade"] == 0

    finally:
        servidor.encerrar()


def test_post_operacao_sem_token_e_recusado(tmp_path):
    _, _, _, servidor = criar_servidor(tmp_path)

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        try:
            requisitar(
                (f"http://127.0.0.1:{porta}" "/operacao/pipeline/executar"),
                metodo="POST",
                token=None,
            )
        except urllib.error.HTTPError as erro:
            assert erro.code == 401
        else:
            raise AssertionError("API aceitou POST operacional sem token.")

    finally:
        servidor.encerrar()
