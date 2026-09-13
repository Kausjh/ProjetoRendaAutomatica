from __future__ import annotations

import inspect

from models.catalogo_canonico import (
    ResultadoObservacaoCatalogoCanonico,
)
from models.oferta import Oferta
from repositories.price_intelligence_repository import (
    PriceIntelligenceRepository,
)
from services.price_intelligence_service import (
    PriceIntelligenceService,
)


def oferta(
    *,
    marketplace: str,
    identificador: str,
    chave: str = "rtx_4060",
    nome: str = "RTX 4060",
    preco: float = 2000.0,
    confianca: float = 95.0,
) -> Oferta:
    item = Oferta(
        nome=nome,
        loja=marketplace,
        preco=preco,
        preco_antigo=None,
        link=("https://example.com/" f"{marketplace}/{identificador}"),
        imagem=None,
        marketplace=marketplace,
        id_anuncio=identificador,
        id_produto=identificador,
    )
    item.produto_canonico = nome
    item.chave_produto_canonica = chave
    item.modelo_produto = nome
    item.confianca_normalizacao = confianca
    return item


def catalogo(
    *,
    marketplace: str,
    identificador: str,
    chave: str = "rtx_4060",
    registrado: bool = True,
) -> ResultadoObservacaoCatalogoCanonico:
    return ResultadoObservacaoCatalogoCanonico(
        status=("anuncio_criado" if registrado else "conflito_anuncio"),
        registrado=registrado,
        chave_canonica=chave,
        marketplace=marketplace,
        identificador_anuncio=identificador,
        motivo="teste",
    )


def criar_service(
    tmp_path,
) -> tuple[
    PriceIntelligenceRepository,
    PriceIntelligenceService,
]:
    repository = PriceIntelligenceRepository(tmp_path / "price_intelligence.sqlite3")
    return (
        repository,
        PriceIntelligenceService(repository),
    )


def test_consolida_mesmo_produto_em_marketplaces_diferentes(
    tmp_path,
):
    repository, service = criar_service(tmp_path)

    service.observar(
        oferta=oferta(
            marketplace="kabum",
            identificador="KB1",
            preco=2100.0,
        ),
        resultado_catalogo=catalogo(
            marketplace="kabum",
            identificador="KB1",
        ),
    )

    service.observar(
        oferta=oferta(
            marketplace="shopee",
            identificador="SH1",
            preco=1950.0,
        ),
        resultado_catalogo=catalogo(
            marketplace="shopee",
            identificador="SH1",
        ),
    )

    snapshot = repository.obter_snapshot("rtx_4060")

    assert snapshot is not None
    assert snapshot.anuncios_observados == 2
    assert snapshot.marketplaces_observados == (
        "kabum",
        "shopee",
    )
    assert snapshot.preco_minimo_atual == 1950.0
    assert snapshot.preco_maximo_atual == 2100.0
    assert snapshot.mediana_atual == 2025.0
    assert snapshot.marketplace_melhor_preco == "shopee"
    assert snapshot.identificador_melhor_preco == "SH1"
    assert snapshot.menor_preco_historico == 1950.0
    assert snapshot.observacoes_historicas == 2

    metricas = repository.obter_metricas()

    assert metricas["produtos"] == 1
    assert metricas["anuncios"] == 2
    assert metricas["observacoes"] == 2
    assert metricas["produtos_multi_marketplace"] == 1


def test_mesmo_preco_nao_duplica_evento_historico(
    tmp_path,
):
    repository, service = criar_service(tmp_path)
    item = oferta(
        marketplace="kabum",
        identificador="KB1",
        preco=2000.0,
    )
    resultado_catalogo = catalogo(
        marketplace="kabum",
        identificador="KB1",
    )

    primeiro = service.observar(
        oferta=item,
        resultado_catalogo=resultado_catalogo,
    )
    segundo = service.observar(
        oferta=item,
        resultado_catalogo=resultado_catalogo,
    )

    assert primeiro.nova_observacao_historica is True
    assert segundo.status == "preco_confirmado_sem_mudanca"
    assert segundo.nova_observacao_historica is False
    assert repository.quantidade_observacoes() == 1


def test_mudanca_de_preco_cria_novo_evento(
    tmp_path,
):
    repository, service = criar_service(tmp_path)
    resultado_catalogo = catalogo(
        marketplace="kabum",
        identificador="KB1",
    )

    service.observar(
        oferta=oferta(
            marketplace="kabum",
            identificador="KB1",
            preco=2000.0,
        ),
        resultado_catalogo=resultado_catalogo,
    )

    resultado = service.observar(
        oferta=oferta(
            marketplace="kabum",
            identificador="KB1",
            preco=1800.0,
        ),
        resultado_catalogo=resultado_catalogo,
    )

    assert resultado.status == "preco_alterado"
    assert resultado.nova_observacao_historica is True
    assert repository.quantidade_observacoes() == 2

    snapshot = repository.obter_snapshot("rtx_4060")

    assert snapshot is not None
    assert snapshot.preco_minimo_atual == 1800.0
    assert snapshot.menor_preco_historico == 1800.0


def test_catalogo_nao_registrado_nao_entra(
    tmp_path,
):
    repository, service = criar_service(tmp_path)

    resultado = service.observar(
        oferta=oferta(
            marketplace="kabum",
            identificador="KB1",
        ),
        resultado_catalogo=catalogo(
            marketplace="kabum",
            identificador="KB1",
            registrado=False,
        ),
    )

    assert resultado.registrado is False
    assert resultado.status == "ignorado_catalogo_nao_registrado"
    assert repository.quantidade_anuncios() == 0


def test_inconsistencia_canonica_falha_fechado(
    tmp_path,
):
    repository, service = criar_service(tmp_path)

    resultado = service.observar(
        oferta=oferta(
            marketplace="kabum",
            identificador="KB1",
            chave="produto_a",
        ),
        resultado_catalogo=catalogo(
            marketplace="kabum",
            identificador="KB1",
            chave="produto_b",
        ),
    )

    assert resultado.registrado is False
    assert resultado.status == "ignorado_inconsistencia_canonica"
    assert repository.quantidade_anuncios() == 0


def test_preco_invalido_e_ignorado(
    tmp_path,
):
    repository, service = criar_service(tmp_path)

    resultado = service.observar(
        oferta=oferta(
            marketplace="kabum",
            identificador="KB1",
            preco=0.0,
        ),
        resultado_catalogo=catalogo(
            marketplace="kabum",
            identificador="KB1",
        ),
    )

    assert resultado.registrado is False
    assert resultado.status == "ignorado_preco_invalido"
    assert repository.quantidade_anuncios() == 0


def test_repository_falha_fechado_em_listing_remapeado(
    tmp_path,
):
    repository = PriceIntelligenceRepository(tmp_path / "price_intelligence.sqlite3")

    status_a, _ = repository.registrar_observacao(
        chave_canonica="produto_a",
        nome_canonico="Produto A",
        marketplace="kabum",
        identificador="KB1",
        preco=100.0,
        link="https://example.com/a",
        observado_em="2026-09-12T20:00:00+00:00",
    )

    status_b, historico_b = repository.registrar_observacao(
        chave_canonica="produto_b",
        nome_canonico="Produto B",
        marketplace="kabum",
        identificador="KB1",
        preco=90.0,
        link="https://example.com/b",
        observado_em="2026-09-12T20:01:00+00:00",
    )

    assert status_a == "preco_inicial_registrado"
    assert status_b == "conflito_identidade"
    assert historico_b is False
    assert repository.quantidade_produtos() == 1
    assert repository.quantidade_anuncios() == 1
    assert repository.quantidade_observacoes() == 1


def test_pipeline_price_intelligence_fica_depois_do_catalogo_e_antes_da_anomalia():
    from services.executor_pipeline import ExecutorPipeline

    fonte = inspect.getsource(ExecutorPipeline.executar)

    normalizacao = fonte.index("self.normalizador_produto.normalizar(oferta)")
    catalogo = fonte.index("self.catalogo_canonico_service.observar(oferta)")
    price = fonte.index("self.price_intelligence_service.observar(")
    anomalia = fonte.index("self.detector_anomalia.avaliar(")

    assert normalizacao < catalogo < price < anomalia


def test_price_intelligence_e_observacional_no_pipeline():
    from services.executor_pipeline import ExecutorPipeline

    fonte = inspect.getsource(ExecutorPipeline.executar)

    inicio = fonte.index("if self.price_intelligence_service is not None")
    trecho = fonte[inicio : inicio + 1800]

    assert "try:" in trecho
    assert "except Exception:" in trecho
    assert "logger.exception" in trecho


def test_main_wira_price_intelligence_persistente():
    import main

    fonte = inspect.getsource(main)

    assert "PriceIntelligenceRepository" in fonte
    assert "PriceIntelligenceService" in fonte
    assert "database/price_intelligence.sqlite3" in fonte
    assert "price_intelligence_service=" "price_intelligence_service" in fonte


def test_v1_nao_reescreve_historicos_legados():
    from pathlib import Path

    for caminho in (
        "services/historico_precos_service.py",
        "services/historico_precos_efetivos_service.py",
        "repositories/historico_precos_repository.py",
        "repositories/historico_precos_efetivos_repository.py",
    ):
        fonte = Path(caminho).read_text(encoding="utf-8-sig")

        assert "PriceIntelligence" not in fonte
        assert "price_intelligence" not in fonte


def test_sqlite_e_fechado_apos_consulta(
    tmp_path,
):
    caminho = tmp_path / "price_intelligence.sqlite3"
    repository = PriceIntelligenceRepository(caminho)

    repository.quantidade_produtos()
    repository.quantidade_anuncios()
    repository.quantidade_observacoes()
    repository.obter_metricas()

    caminho.unlink()

    assert not caminho.exists()


# 63.8738, -149.7525
