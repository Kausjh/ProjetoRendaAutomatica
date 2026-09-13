from __future__ import annotations

import ast
import inspect
from pathlib import Path

from repositories.price_intelligence_repository import (
    PriceIntelligenceRepository,
)
from services.controle.controlador import (
    ControladorAdministrativo,
)


def popular(
    repository: PriceIntelligenceRepository,
) -> None:
    repository.registrar_observacao(
        chave_canonica="rtx_4060",
        nome_canonico="RTX 4060",
        marketplace="kabum",
        identificador="KB1",
        preco=2100.0,
        link="https://example.com/kabum/KB1",
        observado_em="2026-09-12T20:00:00+00:00",
    )
    repository.registrar_observacao(
        chave_canonica="rtx_4060",
        nome_canonico="RTX 4060",
        marketplace="shopee",
        identificador="SH1",
        preco=1950.0,
        link="https://example.com/shopee/SH1",
        observado_em="2026-09-12T20:01:00+00:00",
    )
    repository.registrar_observacao(
        chave_canonica="rtx_4060",
        nome_canonico="RTX 4060",
        marketplace="kabum",
        identificador="KB1",
        preco=2050.0,
        link="https://example.com/kabum/KB1",
        observado_em="2026-09-12T20:02:00+00:00",
    )
    repository.registrar_observacao(
        chave_canonica="ryzen_7_5700x",
        nome_canonico="Ryzen 7 5700X",
        marketplace="mercado_livre",
        identificador="ML1",
        preco=1100.0,
        link="https://example.com/ml/ML1",
        observado_em="2026-09-12T20:03:00+00:00",
    )


def controlador(
    repository: PriceIntelligenceRepository | None,
) -> ControladorAdministrativo:
    item = object.__new__(ControladorAdministrativo)
    item.price_intelligence_repository = repository
    return item


def test_repository_lista_produtos_paginado(
    tmp_path,
):
    repository = PriceIntelligenceRepository(tmp_path / "price.sqlite3")
    popular(repository)

    primeira = repository.listar_produtos(
        limite=1,
        offset=0,
    )
    segunda = repository.listar_produtos(
        limite=1,
        offset=1,
    )

    assert len(primeira) == 1
    assert len(segunda) == 1
    assert primeira[0]["chave_canonica"] != segunda[0]["chave_canonica"]

    rtx = next(item for item in (primeira + segunda) if item["chave_canonica"] == "rtx_4060")

    assert rtx["anuncios_observados"] == 2
    assert rtx["marketplaces_observados"] == 2
    assert rtx["preco_minimo_atual"] == 1950.0
    assert rtx["preco_maximo_atual"] == 2050.0
    assert rtx["marketplace_melhor_preco"] == "shopee"


def test_repository_historico_paginado(
    tmp_path,
):
    repository = PriceIntelligenceRepository(tmp_path / "price.sqlite3")
    popular(repository)

    pagina_1 = repository.listar_historico_paginado(
        "rtx_4060",
        limite=2,
        offset=0,
    )
    pagina_2 = repository.listar_historico_paginado(
        "rtx_4060",
        limite=2,
        offset=2,
    )

    assert len(pagina_1) == 2
    assert len(pagina_2) == 1
    assert pagina_1[0]["observado_em"] > pagina_1[1]["observado_em"]


def test_controller_expoe_metricas_lista_snapshot_e_historico(
    tmp_path,
):
    repository = PriceIntelligenceRepository(tmp_path / "price.sqlite3")
    popular(repository)
    ctrl = controlador(repository)

    metricas = ctrl.obter_metricas_price_intelligence()
    lista = ctrl.listar_price_intelligence(
        limite="10",
        offset="0",
    )
    detalhe = ctrl.obter_price_intelligence("rtx_4060")
    historico = ctrl.listar_historico_price_intelligence(
        "rtx_4060",
        limite="2",
        offset="1",
    )

    assert metricas["disponivel"] is True
    assert metricas["produtos"] == 2
    assert metricas["anuncios"] == 3
    assert metricas["observacoes"] == 4

    assert lista["disponivel"] is True
    assert lista["total"] == 2
    assert len(lista["itens"]) == 2

    assert detalhe["encontrado"] is True
    assert detalhe["snapshot"]["marketplace_melhor_preco"] == "shopee"
    assert len(detalhe["precos_atuais"]) == 2

    assert historico["limite"] == 2
    assert historico["offset"] == 1
    assert len(historico["itens"]) == 2


def test_controller_sem_repository_falha_graciosamente():
    ctrl = controlador(None)

    assert ctrl.obter_metricas_price_intelligence()["disponivel"] is False
    assert ctrl.listar_price_intelligence()["disponivel"] is False
    assert ctrl.obter_price_intelligence("rtx_4060")["disponivel"] is False
    assert ctrl.listar_historico_price_intelligence("rtx_4060")["disponivel"] is False


def test_controller_paginacao_e_limitada(
    tmp_path,
):
    repository = PriceIntelligenceRepository(tmp_path / "price.sqlite3")
    ctrl = controlador(repository)

    resultado = ctrl.listar_price_intelligence(
        limite="999999",
        offset="-50",
    )

    assert resultado["limite"] == 200
    assert resultado["offset"] == 0


def test_api_get_expoe_quatro_rotas_read_only():
    fonte = Path("services/controle/servidor_status.py").read_text(encoding="utf-8-sig")

    for rota in (
        "/price-intelligence/metricas",
        "/price-intelligence/produtos",
        "historico",
    ):
        assert rota in fonte

    tree = ast.parse(fonte)
    do_post = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(
                node,
                ast.FunctionDef,
            )
            and node.name == "do_POST"
        ),
        None,
    )

    if do_post is not None:
        trecho_post = (
            ast.get_source_segment(
                fonte,
                do_post,
            )
            or ""
        )

        assert "/price-intelligence" not in trecho_post


def test_orquestrador_wira_repository_price_intelligence():
    fonte = Path("services/runtime/orquestrador.py").read_text(encoding="utf-8-sig")

    assert "PriceIntelligenceRepository" in fonte
    assert "price_intelligence_repository=" "PriceIntelligenceRepository()" in fonte.replace(
        "\n",
        "",
    ).replace(
        " ",
        "",
    ) or (
        "price_intelligence_repository" in fonte and "PriceIntelligenceRepository()" in fonte
    )


def test_controlador_parametro_price_intelligence_e_opcional():
    parametros = inspect.signature(ControladorAdministrativo.__init__).parameters

    assert "price_intelligence_repository" in parametros
    assert parametros["price_intelligence_repository"].default is None


def test_leituras_nao_mutam_banco(
    tmp_path,
):
    repository = PriceIntelligenceRepository(tmp_path / "price.sqlite3")
    popular(repository)
    ctrl = controlador(repository)

    antes = (
        repository.quantidade_produtos(),
        repository.quantidade_anuncios(),
        repository.quantidade_observacoes(),
    )

    ctrl.obter_metricas_price_intelligence()
    ctrl.listar_price_intelligence()
    ctrl.obter_price_intelligence("rtx_4060")
    ctrl.listar_historico_price_intelligence("rtx_4060")

    depois = (
        repository.quantidade_produtos(),
        repository.quantidade_anuncios(),
        repository.quantidade_observacoes(),
    )

    assert depois == antes


def test_fase2a_nao_da_autoridade_decisoria():
    protegidos = (
        "services/pontuador_oferta.py",
        "services/detector_anomalia_preco.py",
        "services/curadoria_publicacao.py",
        "repositories/fila_publicacao_repository.py",
        "services/historico_precos_service.py",
        "services/historico_precos_efetivos_service.py",
    )

    for caminho in protegidos:
        fonte = Path(caminho).read_text(encoding="utf-8-sig")

        assert "PriceIntelligenceRepository" not in fonte


# 63.8738, -149.7525
