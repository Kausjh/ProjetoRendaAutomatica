from pathlib import Path

from models.alert_engine import (
    TIPO_MUDANCA_PRECO,
    TIPO_NOVO_MENOR_PRECO_HISTORICO,
)
from models.price_intelligence import ResultadoObservacaoPriceIntelligence
from repositories.alert_engine_repository import AlertEngineRepository
from repositories.price_intelligence_repository import (
    PriceIntelligenceRepository,
)
from services.alert_engine_service import AlertEngineService


def _resultado(
    preco,
    *,
    marketplace="kabum",
    identificador="sku-1",
    chave="rtx_5070",
    registrado=True,
    nova=True,
):
    return ResultadoObservacaoPriceIntelligence(
        status="teste",
        registrado=registrado,
        nova_observacao_historica=nova,
        chave_canonica=chave,
        marketplace=marketplace,
        identificador=identificador,
        preco=preco,
        motivo="teste",
    )


def _registrar_pi(
    repo,
    preco,
    *,
    instante,
    marketplace="kabum",
    identificador="sku-1",
    chave="rtx_5070",
):
    repo.registrar_observacao(
        chave_canonica=chave,
        nome_canonico="RTX 5070",
        marketplace=marketplace,
        identificador=identificador,
        preco=preco,
        link=f"https://example.test/{marketplace}/{identificador}",
        observado_em=instante,
    )


def _servico(tmp_path):
    price_repo = PriceIntelligenceRepository(tmp_path / "price.sqlite3")
    alert_repo = AlertEngineRepository(tmp_path / "alert.sqlite3")
    service = AlertEngineService(
        repository=alert_repo,
        price_intelligence_repository=price_repo,
    )
    return price_repo, alert_repo, service


def test_primeira_observacao_cria_baseline_sem_alerta(tmp_path):
    price_repo, alert_repo, service = _servico(tmp_path)
    _registrar_pi(
        price_repo,
        5000,
        instante="2026-09-13T10:00:00+00:00",
    )

    resultado = service.processar(_resultado(5000))

    assert resultado.processado is True
    assert resultado.baseline_inicializada is True
    assert resultado.alertas_gerados == 0
    assert alert_repo.obter_metricas()["eventos"] == 0


def test_queda_gera_mudanca_e_novo_menor(tmp_path):
    price_repo, alert_repo, service = _servico(tmp_path)
    _registrar_pi(
        price_repo,
        5000,
        instante="2026-09-13T10:00:00+00:00",
    )
    service.processar(_resultado(5000))

    _registrar_pi(
        price_repo,
        4500,
        instante="2026-09-13T10:05:00+00:00",
    )
    resultado = service.processar(_resultado(4500))

    assert resultado.alertas_gerados == 2
    assert set(resultado.tipos_gerados) == {
        TIPO_MUDANCA_PRECO,
        TIPO_NOVO_MENOR_PRECO_HISTORICO,
    }


def test_alta_gera_apenas_mudanca(tmp_path):
    price_repo, alert_repo, service = _servico(tmp_path)
    _registrar_pi(
        price_repo,
        4000,
        instante="2026-09-13T10:00:00+00:00",
    )
    service.processar(_resultado(4000))

    _registrar_pi(
        price_repo,
        4200,
        instante="2026-09-13T10:05:00+00:00",
    )
    resultado = service.processar(_resultado(4200))

    assert resultado.tipos_gerados == (TIPO_MUDANCA_PRECO,)
    evento = alert_repo.listar_eventos()[0]
    assert evento["direcao"] == "alta"


def test_nova_listing_pode_gerar_novo_menor_canonico(tmp_path):
    price_repo, _, service = _servico(tmp_path)
    _registrar_pi(
        price_repo,
        5000,
        instante="2026-09-13T10:00:00+00:00",
        marketplace="kabum",
        identificador="a",
    )
    service.processar(_resultado(5000, marketplace="kabum", identificador="a"))

    _registrar_pi(
        price_repo,
        4700,
        instante="2026-09-13T10:05:00+00:00",
        marketplace="shopee",
        identificador="b",
    )
    resultado = service.processar(_resultado(4700, marketplace="shopee", identificador="b"))

    assert resultado.tipos_gerados == (TIPO_NOVO_MENOR_PRECO_HISTORICO,)


def test_reprocessamento_mesmo_preco_e_idempotente(tmp_path):
    price_repo, alert_repo, service = _servico(tmp_path)
    _registrar_pi(
        price_repo,
        5000,
        instante="2026-09-13T10:00:00+00:00",
    )
    service.processar(_resultado(5000))
    _registrar_pi(
        price_repo,
        4500,
        instante="2026-09-13T10:05:00+00:00",
    )

    primeiro = service.processar(_resultado(4500))
    segundo = service.processar(_resultado(4500))

    assert primeiro.alertas_gerados == 2
    assert segundo.alertas_gerados == 0
    assert alert_repo.obter_metricas()["eventos"] == 2


def test_fail_closed_sem_observacao_price_intelligence(tmp_path):
    _, alert_repo, service = _servico(tmp_path)

    resultado = service.processar(_resultado(100, registrado=False, nova=False))

    assert resultado.processado is False
    assert alert_repo.obter_metricas()["eventos"] == 0


def test_alert_engine_nao_importa_entrega_ou_decisores():
    combinado = Path("services/alert_engine_service.py").read_text(encoding="utf-8-sig") + Path(
        "repositories/alert_engine_repository.py"
    ).read_text(encoding="utf-8-sig")

    for proibido in (
        "TelegramBot",
        "send_message",
        "FilaPublicacaoRepository",
        "PontuadorOferta",
        "DetectorAnomaliaPreco",
        "CuradoriaPublicacao",
        "PromotionEngine",
    ):
        assert proibido not in combinado


def test_wiring_pipeline_e_main():
    pipeline = Path("services/executor_pipeline.py").read_text(encoding="utf-8-sig")
    main = Path("main.py").read_text(encoding="utf-8-sig")

    assert "AlertEngineService" in pipeline
    assert "self.alert_engine_service.processar(" in pipeline
    assert "resultado_price_intelligence" in pipeline
    assert "AlertEngineRepository" in main
    assert '"database/alert_engine.sqlite3"' in main
    assert "alert_engine_service=alert_engine_service" in main


def test_bootstrap_popula_estado_sem_eventos(tmp_path):
    price_repo, alert_repo, service = _servico(tmp_path)
    _registrar_pi(
        price_repo,
        5000,
        instante="2026-09-13T10:00:00+00:00",
    )

    resultado = service.bootstrap_estado_atual()
    metricas = alert_repo.obter_metricas()

    assert resultado["produtos_lidos"] == 1
    assert resultado["produtos_inseridos"] == 1
    assert resultado["listings_inseridos"] == 1
    assert resultado["conflitos_identidade"] == 0
    assert metricas["produtos_monitorados"] == 1
    assert metricas["listings_monitorados"] == 1
    assert metricas["eventos"] == 0


def test_bootstrap_e_idempotente_e_nao_sobrescreve_estado(tmp_path):
    price_repo, alert_repo, service = _servico(tmp_path)
    _registrar_pi(
        price_repo,
        5000,
        instante="2026-09-13T10:00:00+00:00",
    )

    primeiro = service.bootstrap_estado_atual()
    segundo = service.bootstrap_estado_atual()

    assert primeiro["produtos_inseridos"] == 1
    assert primeiro["listings_inseridos"] == 1
    assert segundo["produtos_inseridos"] == 0
    assert segundo["listings_inseridos"] == 0
    assert alert_repo.obter_metricas()["eventos"] == 0


def test_primeira_mudanca_futura_nao_e_perdida_apos_bootstrap(tmp_path):
    price_repo, alert_repo, service = _servico(tmp_path)
    _registrar_pi(
        price_repo,
        5000,
        instante="2026-09-13T10:00:00+00:00",
    )
    service.bootstrap_estado_atual()

    _registrar_pi(
        price_repo,
        4500,
        instante="2026-09-13T10:05:00+00:00",
    )
    resultado = service.processar(_resultado(4500))

    assert resultado.alertas_gerados == 2
    assert set(resultado.tipos_gerados) == {
        TIPO_MUDANCA_PRECO,
        TIPO_NOVO_MENOR_PRECO_HISTORICO,
    }
    assert alert_repo.obter_metricas()["eventos"] == 2


def test_main_executa_bootstrap_alert_engine():
    fonte = Path("main.py").read_text(encoding="utf-8-sig")

    assert "alert_engine_service.bootstrap_estado_atual()" in fonte
