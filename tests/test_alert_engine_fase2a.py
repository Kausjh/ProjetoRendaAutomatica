from pathlib import Path

from repositories.alert_engine_repository import AlertEngineRepository
from services.controle.controlador import ControladorAdministrativo


def _controlador(repository):
    controlador = object.__new__(ControladorAdministrativo)
    controlador.alert_engine_repository = repository
    return controlador


def test_repository_estado_produto_read_only(tmp_path):
    repo = AlertEngineRepository(tmp_path / "alert.sqlite3")
    repo.inicializar_baseline(
        chave_canonica="rtx_5070",
        nome_canonico="RTX 5070",
        menor_preco_historico=5000.0,
        listings=[
            ("kabum", "sku-1", 5000.0),
            ("shopee", "sku-2", 5100.0),
        ],
    )

    estado = repo.obter_estado_produto("rtx_5070")

    assert estado is not None
    assert estado["produto"]["chave_canonica"] == "rtx_5070"
    assert len(estado["listings"]) == 2
    assert estado["eventos_total"] == 0
    assert estado["eventos_recentes"] == []


def test_controlador_metricas_e_eventos_paginados(tmp_path):
    repo = AlertEngineRepository(tmp_path / "alert.sqlite3")
    repo.inicializar_baseline(
        chave_canonica="rtx_5070",
        nome_canonico="RTX 5070",
        menor_preco_historico=5000.0,
        listings=[("kabum", "sku-1", 5000.0)],
    )
    repo.processar_observacao(
        chave_canonica="rtx_5070",
        nome_canonico="RTX 5070",
        marketplace="kabum",
        identificador="sku-1",
        preco_atual=4500.0,
        menor_preco_historico=4500.0,
    )

    controlador = _controlador(repo)

    metricas = controlador.obter_metricas_alert_engine()
    eventos = controlador.listar_eventos_alert_engine(
        limite=1,
        offset=0,
    )

    assert metricas["disponivel"] is True
    assert metricas["schema_version"] == 1
    assert metricas["eventos"] == 2
    assert metricas["produtos_monitorados"] == 1
    assert metricas["listings_monitorados"] == 1

    assert eventos["disponivel"] is True
    assert eventos["total"] == 2
    assert eventos["limite"] == 1
    assert eventos["offset"] == 0
    assert len(eventos["itens"]) == 1


def test_controlador_estado_produto(tmp_path):
    repo = AlertEngineRepository(tmp_path / "alert.sqlite3")
    repo.inicializar_baseline(
        chave_canonica="rx_9070_xt",
        nome_canonico="RX 9070 XT",
        menor_preco_historico=4200.0,
        listings=[("kabum", "rx-1", 4200.0)],
    )
    controlador = _controlador(repo)

    encontrado = controlador.obter_estado_produto_alert_engine("rx_9070_xt")
    ausente = controlador.obter_estado_produto_alert_engine("nao_existe")

    assert encontrado["disponivel"] is True
    assert encontrado["encontrado"] is True
    assert encontrado["produto"]["nome_canonico"] == "RX 9070 XT"
    assert len(encontrado["listings"]) == 1

    assert ausente == {
        "disponivel": True,
        "schema_version": 1,
        "encontrado": False,
        "chave_canonica": "nao_existe",
    }


def test_controlador_fail_closed_sem_repository():
    controlador = object.__new__(ControladorAdministrativo)
    controlador.alert_engine_repository = None

    metricas = controlador.obter_metricas_alert_engine()
    eventos = controlador.listar_eventos_alert_engine()
    produto = controlador.obter_estado_produto_alert_engine("rtx_5070")

    assert metricas["disponivel"] is False
    assert eventos["disponivel"] is False
    assert eventos["itens"] == []
    assert produto["disponivel"] is False


def test_rotas_http_alert_engine_sao_get_read_only():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    assert '"/alert-engine/metricas"' in fonte
    assert '"/alert-engine/eventos"' in fonte
    assert 'alert_partes[0] == "alert-engine"' in fonte
    assert 'alert_partes[1] == "produtos"' in fonte

    trecho = fonte.split("def do_GET", 1)[1].split(
        "def do_POST",
        1,
    )[0]
    assert "/alert-engine/" in trecho

    if "def do_POST" in fonte:
        post = fonte.split("def do_POST", 1)[1]
        assert "/alert-engine/" not in post


def test_orquestrador_injeta_alert_engine_repository():
    fonte = Path("services/runtime/orquestrador.py").read_text(encoding="utf-8-sig")

    assert "AlertEngineRepository" in fonte
    assert "alert_engine_repository=AlertEngineRepository()" in fonte
