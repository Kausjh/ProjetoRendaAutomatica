from repositories.fila_publicacao_repository import (
    FilaPublicacaoRepository,
)
from services.controle.controlador import ControladorAdministrativo


class ProcessoFake:
    def __init__(self, pid: int, ativo: bool = True) -> None:
        self.pid = pid
        self.ativo = ativo

    def poll(self) -> int | None:
        return None if self.ativo else 0


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


def test_controle_retrata_estado_do_runtime(tmp_path):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))
    orquestrador = OrquestradorFake()

    controle = ControladorAdministrativo(
        orquestrador=orquestrador,
        fila=fila,
    )

    estado = controle.obter_estado()

    assert estado.runtime_ativo is True
    assert estado.encerrando is False

    assert estado.pipeline.ativo is False
    assert estado.pipeline.pid is None

    assert estado.publicador.ativo is True
    assert estado.publicador.pid == 200

    assert estado.bot.ativo is True
    assert estado.bot.pid == 300

    assert estado.fila.pendentes == 0
    assert estado.fila.familias == 0

    assert estado.conectividade.internet is True
    assert estado.conectividade.telegram is True
    assert estado.conectividade.mercado_livre is True


def test_controle_retrata_runtime_em_encerramento(tmp_path):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))
    orquestrador = OrquestradorFake()
    orquestrador._encerrando = True

    controle = ControladorAdministrativo(
        orquestrador=orquestrador,
        fila=fila,
    )

    estado = controle.obter_estado()

    assert estado.runtime_ativo is False
    assert estado.encerrando is True


def test_estado_pode_ser_serializado_para_api(tmp_path):
    fila = FilaPublicacaoRepository(str(tmp_path / "fila.sqlite3"))
    controle = ControladorAdministrativo(
        orquestrador=OrquestradorFake(),
        fila=fila,
    )

    dados = controle.obter_estado().como_dict()

    assert dados["runtime_ativo"] is True
    assert dados["publicador"]["pid"] == 200
    assert dados["fila"]["pendentes"] == 0
    assert dados["conectividade"]["telegram"] is True
