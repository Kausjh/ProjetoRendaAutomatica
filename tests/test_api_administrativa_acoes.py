from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

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


def test_post_modo_manual_persiste_e_audita(tmp_path):
    _, admin, _, servidor = criar_servidor(tmp_path)

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status, dados = requisitar(
            f"http://127.0.0.1:{porta}/operacao/modo/manual",
            metodo="POST",
        )

        assert status == 200
        assert dados["operacao"]["modo_operacao"] == "manual"
        assert admin.obter_modo_operacao() == "manual"

        auditoria = admin.listar_auditoria(limite=10)

        assert auditoria[0]["acao"] == "operacao.modo.manual"
        assert auditoria[0]["detalhes"]["novo"] == "manual"

    finally:
        servidor.encerrar()


def test_post_fila_segurar_reflete_na_api(tmp_path):
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

        status, _ = requisitar(
            f"http://127.0.0.1:{porta}/fila/{item_id}/segurar-15",
            metodo="POST",
        )

        assert status == 200

        _, dados_fila = requisitar(f"http://127.0.0.1:{porta}/fila")

        item = dados_fila["itens"][0]

        assert item["estado_agenda"] == "segurado"
        assert item["segurado_ate"] is not None
        assert item["previsao_publicacao"] is not None

        auditoria = admin.listar_auditoria(limite=10)

        assert auditoria[0]["acao"] == "fila.segurar-15"
        assert auditoria[0]["detalhes"]["minutos"] == 15

    finally:
        servidor.encerrar()


def test_post_fila_agendar_e_liberar(tmp_path):
    fila, _, _, servidor = criar_servidor(tmp_path)

    fila.adicionar_ou_atualizar(
        oferta=criar_oferta(),
        resultado_historico=None,
        pontuacao=90.0,
        deve_republicar_por_queda=False,
        prioridade=80.0,
    )

    item_id = fila.listar_pendentes(limite=1)[0].id
    para = (datetime.now().astimezone() + timedelta(minutes=20)).replace(microsecond=0)
    para_url = urllib.parse.quote(
        para.isoformat(),
        safe="",
    )

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status, _ = requisitar(
            (f"http://127.0.0.1:{porta}" f"/fila/{item_id}/agendar?para={para_url}"),
            metodo="POST",
        )

        assert status == 200

        _, agenda = requisitar(f"http://127.0.0.1:{porta}/agenda")

        assert agenda["quantidade"] == 1
        assert agenda["itens"][0]["estado_agenda"] == "agendado"
        assert agenda["itens"][0]["agendado_para"] == para.isoformat()

        status_liberar, _ = requisitar(
            f"http://127.0.0.1:{porta}/fila/{item_id}/liberar",
            metodo="POST",
        )

        assert status_liberar == 200

        _, fila_liberada = requisitar(f"http://127.0.0.1:{porta}/fila")

        assert fila_liberada["itens"][0]["agendado_para"] is None
        assert fila_liberada["itens"][0]["segurado_ate"] is None

    finally:
        servidor.encerrar()


def test_modo_hibrido_exige_aprovacao_para_score_baixo(tmp_path):
    fila, _, _, servidor = criar_servidor(tmp_path)

    fila.adicionar_ou_atualizar(
        oferta=criar_oferta(),
        resultado_historico=None,
        pontuacao=75.0,
        deve_republicar_por_queda=False,
        prioridade=80.0,
    )

    item_id = fila.listar_pendentes(limite=1)[0].id

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        requisitar(
            f"http://127.0.0.1:{porta}/operacao/modo/hibrido",
            metodo="POST",
        )

        _, dados_fila = requisitar(f"http://127.0.0.1:{porta}/fila")

        item = dados_fila["itens"][0]

        assert item["requer_aprovacao_hibrida"] is True
        assert item["estado_agenda"] == "aguardando_aprovacao"
        assert item["previsao_publicacao"] is None

        status_aprovar, _ = requisitar(
            f"http://127.0.0.1:{porta}/fila/{item_id}/aprovar",
            metodo="POST",
        )

        assert status_aprovar == 200

        _, dados_aprovados = requisitar(f"http://127.0.0.1:{porta}/fila")

        item_aprovado = dados_aprovados["itens"][0]

        assert item_aprovado["aprovado_manualmente"] is True
        assert item_aprovado["requer_aprovacao_hibrida"] is False
        assert item_aprovado["estado_agenda"] == "liberado"
        assert item_aprovado["previsao_publicacao"] is not None

    finally:
        servidor.encerrar()


def test_operacao_nao_expoe_previsao_vencida_sem_fila(tmp_path):
    _, admin, _, servidor = criar_servidor(tmp_path)

    previsao_vencida = (datetime.now().astimezone() - timedelta(minutes=10)).replace(microsecond=0)

    admin.definir_estado(
        "proxima_publicacao_estimada_em",
        previsao_vencida.isoformat(),
    )

    servidor.iniciar()

    try:
        porta = servidor._servidor.server_address[1]

        status, operacao = requisitar(f"http://127.0.0.1:{porta}/operacao")

        assert status == 200
        assert operacao["proxima_publicacao_estimada_em"] is None

    finally:
        servidor.encerrar()
